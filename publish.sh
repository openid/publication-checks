#!/bin/bash
DEBUG=false
# Enable debug mode if the DEBUG environment variable is set
DEBUG=${DEBUG:-false}
ANYFAILS=0
publishedlinks=""

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
        debug_print -e "There is no $1 in $2"
        debug_print -e "output:"
        echo -e "cli_tool.py $output"
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
if ! run_cli_tool "-get-spec-list-csv" "-output"  "spec-list.csv" "Fetching OpenID Specs list"; then
    echo_error "OpenID Specs not available. Exiting script."
    exit 1
fi

# Get the list of changed HTML files
changed_files=$(git -C ../. diff --name-only origin/main...HEAD | grep '\.html$')
echo $changed_files > delete_files.txt
pwd
ls -l
echo "Number of new files detected: "$(echo_info "$changed_files" | wc -l)""
debug_print $changed_files
export CHANGEDFILES=$changed_files
echo "List of changed files detected: "
for file in $changed_files; do
    echo_info "$file"
    subdirectories+=$(dirname "$file")
    subdirectories+=" "
done
echo "Sub-Directories: $(echo $subdirectories | tr " " "\n" | sort -u | uniq | wc -w)"

# Check if there are any changed HTML files
if [ -z "$changed_files" ]; then
    echo_error "FAIL: No HTML files have changed.  Exiting script."
    exit 1
fi

# Loop through each changed HTML file
for file in $changed_files; do
    HTMLFAILS=0
    ZIPFAILS=0
    MDFAILS=0
    XMLFAILS=0
    TXTFAILS=0
    COPYFAILS=0
    DOCFAILS=0

    echo "------------------------------------------------------------------------------------------------------------------"
    echo "Processing file: $file"

    # Check document state
    state_output=$(run_cli_tool "-content-state" "../$file")
    echo $state_output
    
    # Extract the state from the output
    state=$(echo "$state_output" | grep "state:" | awk '{print $NF}' | tr -d '[:space:]')
    
    versionedname=$(basename "${file%.html}")
    debug_print $versionedname
    unversionedname=${versionedname:0:-3}
    debug_print $unversionedname
    
    case "$state" in
        UNKNOWN )
            echo_error "Problem with document titles so state is UNKNOWN.  EXITING"
            COPYFAILS=1
            exit 1
            ;;
        DRAFT )
            echo "Do DRAFT copies"
            # copy .html to and non version suffix to-publish - mandatory success
            if $(cp ../$file ../to-publish/$(basename "$file") 2>/dev/null); then
                publishedlinks+="https://openid.net/specs/$(basename "$file") "
                mv ../$file ../to-publish/$unversionedname.html
                publishedlinks+="https://openid.net/specs/$unversionedname.html "
                echo "successful html copies"
            else
                echo_error "ERROR: Mandatory copy of $file failed"
                HTMLFAILS=1
            fi
            # copy spec-x_0-01.zip to non version suffix copy - mandatory success
            if $(cp ../$(dirname $file)/$versionedname.zip ../to-publish/$versionedname.zip 2>/dev/null); then
                publishedlinks+="https://openid.net/specs/$versionedname.zip "
                mv ../$(dirname $file)/$versionedname.zip ../to-publish/$unversionedname.zip
                publishedlinks+="https://openid.net/specs/$unversionedname.zip "
                echo "successful zip copies"
            else
                echo_warn "WARNING: copy of $versionedname.zip failed"
                ZIPFAILS=1
            fi

            # copy spec-x_0-01.md to non version suffix copy 
            if $(cp ../$(dirname $file)/$versionedname.md ../to-publish/$versionedname.md 2>/dev/null); then
                publishedlinks+="https://openid.net/specs/$versionedname.md "
                mv ../$(dirname $file)/$versionedname.md ../to-publish/$unversionedname.md
                publishedlinks+="https://openid.net/specs/$unversionedname.md "
                echo "successful md copies"
            else
                echo_warn "WARNING: copy of $versionedname.md failed"
                MDFAILS=1
            fi
            # copy spec-x_0-01.xml to non version suffix copy
            if $(cp ../$(dirname $file)/$versionedname.xml ../to-publish/$versionedname.xml 2>/dev/null); then
                publishedlinks+="https://openid.net/specs/$versionedname.xml "
                mv ../$(dirname $file)/$versionedname.xml ../to-publish/$unversionedname.xml
                publishedlinks+="https://openid.net/specs/$unversionedname.xml "
                echo "successful xml copies"
            else
                echo_warn "WARNING: copy of $versionedname.xml failed"
                XMLFAILS=1
            fi
        
            # copy spec-x_0-01.txt to non version suffix copy - optional
            if $(cp ../$(dirname $file)/$versionedname.txt ../to-publish/$versionedname.txt 2>/dev/null); then
                publishedlinks+="https://openid.net/specs/$versionedname.txt "
                mv ../$(dirname $file)/$versionedname.txt ../to-publish/$unversionedname.txt
                publishedlinks+="https://openid.net/specs/$unversionedname.txt "
                echo "successful txt copies"
            else
                echo_warn "WARNING: copy of $versionedname.txt failed"
                TXTFAILS=1
            fi            
            ;;
        FINAL )
            echo "Do FINAL copies"
            # copy spec-x_0-01.html to non version suffix copy and -final suffix - mandatory success
            if $(cp ../$file ../to-publish/$(basename "$file") 2>/dev/null); then
                publishedlinks+="https://openid.net/specs/$(basename "$file") "
                cp ../$file ../to-publish/$unversionedname.html
                publishedlinks+="https://openid.net/specs/$unversionedname.html "
                mv ../$file ../to-publish/$unversionedname-final.html
                publishedlinks+="https://openid.net/specs/$unversionedname-final.html "
                echo "successful html copies"
            else
                echo_error "ERROR: Mandatory copy of $file failed"
                HTMLFAILS=1
            fi
            # copy spec-x_0-01.zip to non version suffix copy and -final suffix - mandatory success
            if $(cp ../$(dirname $file)/$versionedname.zip ../to-publish/$versionedname.zip 2>/dev/null); then
                publishedlinks+="https://openid.net/specs/$versionedname.zip "
                cp ../$(dirname $file)/$versionedname.zip ../to-publish/$unversionedname.zip
                publishedlinks+="https://openid.net/specs/$unversionedname.zip "
                mv ../$(dirname $file)/$versionedname.zip ../to-publish/$unversionedname-final.zip
                publishedlinks+="https://openid.net/specs/$unversionedname-final.zip "
                echo "successful zip copies"
            else
                echo_warn "WARNING: copy of $versionedname.zip failed"
                ZIPFAILS=1
            fi
    # md or xml are required
            # copy spec-x_0-01.md to non version suffix copy and -final suffix 
            if $(cp ../$(dirname $file)/$versionedname.md ../to-publish/$versionedname.md 2>/dev/null); then
                publishedlinks+="https://openid.net/specs/$versionedname.md "
                cp ../$(dirname $file)/$versionedname.md ../to-publish/$unversionedname.md
                publishedlinks+="https://openid.net/specs/$unversionedname.md "
                mv ../$(dirname $file)/$versionedname.md ../to-publish/$unversionedname-final.md
                publishedlinks+="https://openid.net/specs/$unversionedname-final.md "
                echo "successful md copies"
            else
                echo_warn "WARNING copy of $versionedname.md failed"
                MDFAILS=1
            fi
            # copy spec-x_0-01.xml to non version suffix copy and -final suffix
            if $(cp ../$(dirname $file)/$versionedname.xml ../to-publish/$versionedname.xml 2>/dev/null); then
                publishedlinks+="https://openid.net/specs/$versionedname.xml "
                cp ../$(dirname $file)/$versionedname.xml ../to-publish/$unversionedname.xml
                publishedlinks+="https://openid.net/specs/$unversionedname.xml "
                mv ../$(dirname $file)/$versionedname.xml ../to-publish/$unversionedname-final.xml
                publishedlinks+="https://openid.net/specs/$unversionedname-final.xml "
                echo "successful xml copies"
            else
                echo_warn "WARNING copy of $versionedname.xml failed"
                XMLFAILS=1
            fi
            # copy spec-x_0-01.txt to non version suffix copy and -final suffix - optional
            if $(cp ../$(dirname $file)/$versionedname.txt ../to-publish/$versionedname.txt 2>/dev/null); then
                publishedlinks+="https://openid.net/specs/$versionedname.txt "
                cp ../$(dirname $file)/$versionedname.txt ../to-publish/$unversionedname.txt
                publishedlinks+="https://openid.net/specs/$unversionedname.txt "
                mv ../$(dirname $file)/$versionedname.txt ../to-publish/$unversionedname-final.txt
                publishedlinks+="https://openid.net/specs/$unversionedname-final.txt "
                echo "successful txt copies"
            else
                echo_warn "WARNING copy of $versionedname.txt failed"
                TXTFAILS=1
            fi
            ;;
        ERRATA )
            echo "Do ERRATA copies"
            # work out what the incremental number should be
            existingerratarows=$(grep -E  "$unversionedname-errata.\.html" spec-list.csv | cut -d "," -f 1)
            # grep "$unversionedname-errata" spec-list.csv
            existing_errata=""
            for row in $existingerratarows; do
                basenameoferrata=$(basename "${row%.html}")
                existing_errata+="${basenameoferrata:(-1)} "
            done
            current_max_errata=$(echo $existing_errata | tr " " "\n" | sort -nu | tail -1)
            next_errata=$(($current_max_errata+1))
            echo "Next Errata increment: $next_errata"

            # copy spec-x_0-01.html to non version suffix copy and incremented errata suffix - mandatory success
            if $(cp ../$file ../to-publish/$(basename "$file") 2>/dev/null); then
                publishedlinks+="https://openid.net/specs/$(basename "$file") "
                cp ../$file ../to-publish/$unversionedname.html
                publishedlinks+="https://openid.net/specs/$unversionedname.html "
                mv ../$file ../to-publish/$unversionedname-errata$next_errata.html
                publishedlinks+="https://openid.net/specs/$unversionedname-errata$next_errata.html "
                echo "successful html copies"
            else
                echo_error "ERROR: Mandatory copy of $file failed"
                HTMLFAILS=1
            fi
            # copy spec-x_0-01.zip to non version suffix copy and -final suffix - mandatory success
            if $(cp ../$(dirname $file)/$versionedname.zip ../to-publish/$versionedname.zip 2>/dev/null); then
                publishedlinks+="https://openid.net/specs/$versionedname.zip "
                cp ../$(dirname $file)/$versionedname.zip ../to-publish/$unversionedname.zip
                publishedlinks+="https://openid.net/specs/$unversionedname.zip "
                mv ../$(dirname $file)/$versionedname.zip ../to-publish/$unversionedname-final.zip
                publishedlinks+="https://openid.net/specs/$unversionedname-errata$next_errata.zip "
                echo "successful zip copies"
            else
                echo_warn "WARNING: copy of $versionedname.zip failed"
                ZIPFAILS=1
            fi
            # md or xml are required
                # copy spec-x_0-01.md to non version suffix copy and -final suffix
            if $(cp ../$(dirname $file)/$versionedname.md ../to-publish/$versionedname.md 2>/dev/null); then
                publishedlinks+="https://openid.net/specs/$versionedname.md "
                cp ../$(dirname $file)/$versionedname.md ../to-publish/$unversionedname.md
                publishedlinks+="https://openid.net/specs/$unversionedname.md "
                mv ../$(dirname $file)/$versionedname.md ../to-publish/$unversionedname-final.md
                publishedlinks+="https://openid.net/specs/$unversionedname-errata$next_errata.md "
                echo "successful md copies"
            else
                echo_warn "WARNING: Copy of $versionedname.md failed"
                MDFAILS=1
            fi
                # copy spec-x_0-01.xml to non version suffix copy and -final suffix
            if $(cp ../$(dirname $file)/$versionedname.xml ../to-publish/$versionedname.xml 2>/dev/null); then
                publishedlinks+="https://openid.net/specs/$versionedname.xml "
                cp ../$(dirname $file)/$versionedname.xml ../to-publish/$unversionedname.xml
                publishedlinks+="https://openid.net/specs/$unversionedname.xml "
                mv ../$(dirname $file)/$versionedname.xml ../to-publish/$unversionedname-final.xml
                publishedlinks+="https://openid.net/specs/$unversionedname-errata$next_errata.xml "
                echo "successful xml copies"
            else
                echo_warn "WARNING: Copy of $versionedname.xml failed"
                MDFAILS=1
            fi
            # copy spec-x_0-01.txt to non version suffix copy and -final suffix - optional
            if $(cp ../$(dirname $file)/$versionedname.txt ../to-publish/$versionedname.txt 2>/dev/null); then
                publishedlinks+="https://openid.net/specs/$versionedname.txt "
                cp ../$(dirname $file)/$versionedname.txt ../to-publish/$unversionedname.txt
                publishedlinks+="https://openid.net/specs/$unversionedname.txt "
                mv ../$(dirname $file)/$versionedname.txt ../to-publish/$unversionedname-final.txt
                publishedlinks+="https://openid.net/specs/$unversionedname-errata$next_errata.txt "
                echo "successful txt copies"
            else
                echo_warn "WARNING: Copy of $versionedname.txt failed"
                TXTFAILS=1
            fi

            ;;
        * )
            echo_error "FAIL: Unexpected document state: $state"
            echo_error "FAIL: this may be due to incorrect file name format or heading suffix issues"
            COPYFAILS=1
            ;;
    esac

# either md or xml are required

    if [ $COPYFAILS == 1 ] || [ $HTMLFAILS == 1 ]
    then 
        echo_error "FAIL: $file either a file state error or HTML copy error occured"
        ANYFAILS=1
        DOCFAILS=1
    fi

    if [[ $MDFAILS == "1" ]] && [[ $XMLFAILS == "1" ]];
    then 
        echo_error "FAIL: $file requires corresponding source as either .md or .xml"
        ANYFAILS=1
        DOCFAILS=1
    fi

    if [ $DOCFAILS == 1 ]; then
        echo_error "FAIL: $file did not pass all checks"
    else
        echo_good "CONGRATULATIONS: $file prepartion successful"
    fi

    echo "------------------------------------------------------------------------------------------------------------------"
done

echo "All checks completed"

if [ $ANYFAILS == "1" ]
then 
    echo_error "Process exiting in a fail state - there was a critical failure with on or more of the documents" 
    exit 1
fi

echo_good "CONGRATULATIONS: publish prep complete"
echo_good "Links:"

for link in $publishedlinks; do
    echo_good $link
done
    echo "------------------------------------------------------------------------------------------------------------------"
    echo "------------------------------------------------------------------------------------------------------------------"
exit 0


