#!/bin/bash
DEBUG=false
# Enable debug mode if the DEBUG environment variable is set
DEBUG=${DEBUG:-false}

# Function to print debug messages
debug_print() {
    if [ "$DEBUG" = true ]; then
        echo "$@"
    fi
}

# Define color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m'

# Define color print functions
echo_error() {
    printf "${RED}%s${NC}\n" "$1"
}
echo_warn() {
    printf "${YELLOW}%s${NC}\n" "$1"
}
echo_good() {
    printf "${GREEN}%s${NC}\n" "$1"
}
echo_info() {
    printf "${CYAN}%s${NC}\n" "$1"
}

# Function to run cli-tool.py and check exit status
run_cli_tool() {
    output=$(python cli-tool.py "$@" 2>&1)
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo -e "There is no $1 in $2"
        echo -e "output:"
        echo -e "$output"
        return 1
    else
        echo -e "Running $1"
        if [ "$1" = "-content-state" ] || [ "$1" = "-content-date" ] || [ "$1" = "-content-history" ] || [ "$1" = "-content-ref -check-url" ]; then
            echo "$output"  # Display full output for content-state
        else
            debug_print "$output"
        fi
        return 0
    fi
}

# Fetch OpenID Specs list
if ! run_cli_tool "-get-spec-list-csv" "-output" "spec-list.csv" "Fetching OpenID Specs list"; then
    echo_error "OpenID Specs not available. Exiting script."
    exit 1
fi

# Get the list of changed HTML files
changed_files=$(git -C ../. diff --name-only origin/main...HEAD | grep '\.html$')
echo "Number of new files detected: "$(echo_info "$changed_files" | wc -l)""
debug_print $changed_files
echo "List of changed files detected: "
for file in $changed_files; do
    echo_info "$file"
    subdirectories+=$(dirname "$file")
    subdirectories+=" "
done

# Check if there are any changed HTML files
if [ -z "$changed_files" ]; then
    echo_error "FAIL: No HTML files have changed.  Exiting script."
    exit 1
fi

# Check that only one sub-directory is changed
numofwg=$(echo $subdirectories | tr " " "\n" | sort -u | uniq | wc -w)
if [ $numofwg != 1 ]; then
    echo_error "FAIL: More than one WG sub-directory updated."
    WGFAILS=1
fi

# Loop through each changed HTML file
for file in $changed_files; do
    DOCFAILS=0
    echo "------------------------------------------------------------------------------------------------------------------"
    echo "Processing file: $file"

    # Are there sufficient source files?
    if [ DEBUG ]; then 
        ls ../${file%.html}.zip 1>/dev/null 2>/dev/null
        ZIPEXISTS=$?
        ls ../${file%.html}.txt 1>/dev/null 2>/dev/null
        TXTEXISTS=$?
        ls ../${file%.html}.md 1>/dev/null 2>/dev/null
        MDEXISTS=$?
        ls ../${file%.html}.xml 1>/dev/null 2>/dev/null
        XMLEXISTS=$?
        debug_print "ZIP Status: $ZIPEXISTS"
        debug_print "TXT Status: $TXTEXISTS"
        debug_print "MD Status: $MDEXISTS"
        debug_print "XML Status: $XMLEXISTS"
    fi

    # Check if the file already exists using -check-draft
    if ! run_cli_tool "-check-draft" "$file" "Checking if file exists"; then
        echo_error "FAIL: File $file already exists."
        DOCFAILS=1
        else
        echo_good "PASS: $file does not already exist"
    fi

    if [ ! -f "../${file%.html}.zip" ]; then
        echo_warn "WARNING: zipped content called ${file%.html}.zip not present."
    fi

    if [ ! -f "../${file%.html}.md" ] && [ ! -f "../${file%.html}.xml" ]; then
        echo_error "FAIL: Either Markdown or XML Source is required. Either a file called ${file%.html}.md or called ${file%.html}.xml is required."
        DOCFAILS=1
    fi

    # Check for history section
    has_history=false
    history_output=$(run_cli_tool "-content-history" "../$file")
    if echo "$history_output" | grep -q "history_present: True"; then
        has_history=true
    fi

    # Check document state
    state_output=$(run_cli_tool "-content-state" "../$file")
    
    # Extract the state from the output
    state=$(echo "$state_output" | grep "state:" | awk '{print $NF}' | tr -d '[:space:]')
    
    versionedname=$(basename "${file%.html}")
    debug_print $versionedname
    unversionedname=${versionedname:0:-3}
    debug_print $unversionedname

    case "$state" in
        UNKNOWN )
            echo_error "FAIL: Problem with document titles so state is UNKNOWN"
            DOCFAILS=1
            ;;
        DRAFT )
            if [ "$has_history" = true ]; then
                echo_good "Document is in DRAFT state"
                echo_good "PASS: Document has a history section"
            else
                echo_good "Document is in DRAFT state"
                echo_error "FAIL: DRAFT state but does not have required history section"
                DOCFAILS=1
            fi
            ;;
        FINAL )
            if [ "$has_history" = false ]; then
                echo_good "Document is in FINAL state"
                echo_good "PASS: Document does not have a history section"
            else
                echo_good "Document is in FINAL state"
                echo_error "FAIL: FINAL state but history section exists"
                DOCFAILS=1
            fi
            ;;
        ERRATA )
            # check errata does not have a history section
            if [ "$has_history" = false ]; then
                echo_good "Document is in ERRATA state"
                echo_good "PASS: Document does not have a history section"
            else
                echo_good "Document is in ERRATA state"
                echo_error "FAIL: ERRATA state but history section exists"
                DOCFAILS=1
            fi
            # check that there is a precursor final on specs directory
            existingfinal=$(grep -E  "$unversionedname-final.html" spec-list.csv | cut -d "," -f 1)
            debug_print $existingfinal
            if ! [ -z $existingfinal ]; then
                echo_good "PASS: A predecessor final spec exists"
            else
                echo_error "FAIL: A predecessor final spec does not exist"
                DOCFAILS=1
            fi
            ;;
        * )
            echo_error "FAIL: Unexpected document state: $state"
            echo_error "FAIL: this may be due to incorrect file name format or heading suffix issues"
            DOCFAILS=1
            ;;
    esac
    
    # Run content checks
    ## Content Authors
    if ! run_cli_tool "-content-authors" "../$file"; then
        echo_error "FAIL: Problem with authors in $file."
        DOCFAILS=1
        else
        echo_good "PASS: Authors section in $file is good"
    fi

    ## Content Notices
    if ! run_cli_tool "-content-notices" "../$file"; then
        echo_error "FAIL: Problem with Notices section in $file."
        DOCFAILS=1
        else
        echo_good "PASS: Notices section in $file is good"
    fi

    ## Content References
    if ! run_cli_tool "-content-ref" "-check-url" "../$file"; then
        echo_error "FAIL: Problem with References in $file."
        echo_error "This might be due to a link not responding to HEAD request - ** known roadmap defect in this tool"
        DOCFAILS=1
        else
        echo_good "PASS: References in $file is good"
    fi

    ## Content Structure
    if ! run_cli_tool "-content-struct" "../$file"; then
        echo_error "FAIL: Problem with structure in $file."
        DOCFAILS=1
        else
        echo_good "PASS: Structure of $file is good"
        echo_good " This indicates that Abstract, Introduction, References, Normative References, Informative References, Acknowledgements and Security Considerations sections are all present"
    fi

    # Output content date
    today=$(date '+%Y-%m-%d')
    echo "Today is: $today"
    days_old="unset"
    date_output=$(run_cli_tool "-content-date" "-date" "$today" "../$file")
    days_old=$(echo $date_output | grep 'difference' | cut -d " " -f 17 | tr -d ,)
    echo "$days_old days since publication" 
    if [ "$days_old" -gt 10 ]; then
        echo_error "FAIL: Publication date is more than 10 days ago in $file."
        DOCFAILS=1
        else
        echo_good "PASS: Publication date of $file is good"
    fi
 
    if [ $DOCFAILS == "1" ]
    then 
        ANYFAILS=1
        echo_error "FAIL: $file did not pass all checks"
    else
        echo_good "CONGRATULATIONS: $file passed all checks"
    fi
    echo "------------------------------------------------------------------------------------------------------------------"
    echo "------------------------------------------------------------------------------------------------------------------"
done

echo "All checks completed"

if [ "$DOCFAILS" == "1" ] || [ "$WGFAILS" == "1" ]; then
    ANYFAILS=1
fi

if [ $ANYFAILS == "1" ]
then 
    echo_error "Process exiting in a fail state - one or more of the submitted html documents failed at least one check" 
    echo_error "Guidance on how to fix each FAIL state is provided at https://github.com/openid/publication/blob/main/ERROR-MODES.md"
    exit 1
fi

echo_good "CONGRATULATIONS: all submitted files passed all checks"
    echo "------------------------------------------------------------------------------------------------------------------"
exit 0


