#!/bin/bash
DEBUG=false
# Enable debug mode if the DEBUG environment variable is set
DEBUG=${DEBUG:-false}
REPO="publication-checks"

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
    pwd
    ls
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
    echo -e "\e[31m: OpenID Specs not available. Exiting script."
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
    echo -e "\e[31mFAIL: No HTML files have changed.  Exiting script."
    exit 1
fi

# Check that only one sub-directory is changed
numofwg=$(echo $subdirectories | tr " " "\n" | sort -u | uniq | wc -w)
if [ $numofwg != 1 ]; then
    echo -e "\e[31mFAIL: More than one WG sub-directory updated."
    DOCFAILS=0
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
        echo_error "FAIL: zipped content called ${file%.html}.zip missing."
        DOCFAILS=1
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
    uname -a
    state_output=$(run_cli_tool "-content-state" "../$file")
    echo_info $state_output
    
    # Extract the state from the output
    state=$(echo "$state_output" | grep "state:" | awk '{print $NF}' | tr -d '[:space:]')
    echo_info $state
    
    case "$state" in
        UNKNOWN )
            echo -e "\e[31mFAIL: Problem with document titles so state is UNKNOWN"
            DOCFAILS=1
            ;;
        DRAFT )
            if [ "$has_history" = true ]; then
                echo -e "\e[32mDocument is in DRAFT state"
                echo -e "\e[32mPASS: Document has a history section"
            else
                echo -e "\e[32mDocument is in DRAFT state"
                echo -e "\e[31mFAIL: DRAFT state but does not have required history section"
                DOCFAILS=1
            fi
            ;;
        FINAL )
            if [ "$has_history" = false ]; then
                echo -e "\e[32mDocument is in FINAL state"
                echo -e "\e[32mPASS: Document does not have a history section"
            else
                echo -e "\e[32mDocument is in FINAL state"
                echo -e "\e[31mFAIL: FINAL state but history section exists"
                DOCFAILS=1
            fi
            ;;
        ERRATA )
            if [ "$has_history" = false ]; then
                echo -e "\e[32mDocument is in ERRATA state"
                echo -e "\e[32mPASS: Document does not have a history section"
            else
                echo -e "\e[32mDocument is in ERRATA state"
                echo -e "\e[31mFAIL: ERRATA state but history section exists"
                DOCFAILS=1
            fi
            ;;
        * )
            echo -e "\e[31mFAIL: Unexpected document state: $state"
            echo -e "\e[31mFAIL: this may be due to incorrect file name format or heading suffix issues"
            DOCFAILS=1
            ;;
    esac
    
    # Run content checks
    ## Content Authors
    if ! run_cli_tool "-content-authors" "../$file"; then
        echo -e "\e[31mFAIL: Problem with authors in $file."
        DOCFAILS=1
        else
        echo -e "\e[32mPASS: Authors section in $file is good"
    fi

    ## Content Notices
    if ! run_cli_tool "-content-notices" "../$file"; then
        echo -e "\e[31mFAIL: Problem with Notices section in $file."
        DOCFAILS=1
        else
        echo -e "\e[32mPASS: Notices section in $file is good"
    fi

    ## Content References
    if ! run_cli_tool "-content-ref -check-url" "../$file"; then
        echo -e "\e[31mFAIL: Problem with References in $file."
        DOCFAILS=1
        else
        echo -e "\e[32mPASS: References in $file is good"
    fi

    ## Content Structure
    if ! run_cli_tool "-content-struct" "../$file"; then
        echo -e "\e[31mFAIL: Problem with structure in $file."
        DOCFAILS=1
        else
        echo -e "\e[32mPASS: Structure of $file is good"
        echo -e "\e[32m This indicates that Abstract, Introduction, References, Normative References, Informative References, Acknowledgements and Security Considerations sections are all present"
    fi

    # Output content date
    today=$(date '+%Y-%m-%d')
    echo "Today is: $today"
    days_old="unset"
    date_output=$(run_cli_tool "-content-date" "-date" "$today" "../$file")
#echo $date_output | grep 'difference' | cut -d " " -f 11 | tr -d ,
    days_old=$(echo $date_output | grep 'difference' | cut -d " " -f 11 | tr -d ,)
    echo "$days_old days since publication" 
    if [ "$days_old" -gt 10 ]; then
        echo -e "\e[31mFAIL: Publication date is more than 10 days ago in $file."
        DOCFAILS=1
        else
        echo -e "\e[32mPASS: Publication date of $file is good"
    fi
 
    if [ $DOCFAILS == "1" ]
    then 
        ANYFAILS=1
        echo -e "\e[31mFAIL: $file did not pass all checks"
    else
        echo -e "\e[32mCONGRATULATIONS: $file passed all checks"
    fi
    echo "------------------------------------------------------------------------------------------------------------------"
    echo "------------------------------------------------------------------------------------------------------------------"
done

echo "All checks completed"

if [ $ANYFAILS == "1" ]
then 
    echo -e "\e[31mProcess exiting in a fail state - one or more of the submitted html documents failed at least one check" 
    exit 1
fi

echo -e "\e[32mCONGRATULATIONS: all submitted files passed all checks"
    echo "------------------------------------------------------------------------------------------------------------------"
exit 0


