# OIDF publication-checks
Code repo for shell script and python that perform OIDF publication automated checks

# OpenID Specification tooling
This repository contains tooling for the automation of the verification
of proposed for publication by the OpenID Foundation to https://openid.net/specs

This tooling checks proposed documents that are delivered in html and the filename
being in the submission form

* It starts with lowercase letters, numbers, and hyphens.
* It must include at least one number after a hyphen.
* It ends with an underscore, some numbers, another hyphen, final set of numbers.
* The file extension must be ".html".

For example, it might match filenames like:

* __proposed-spec-123_456-78.html__
* __other-proposed-draft-1_2-30.html__

# cli-tool.py
This tool applies regular expressions to process the html content of proposed
standards and confirms their content matches particularly requirements

It can also (dependant on options chosen) download specifications and their published information
from [OpenID Specification repository](https://openid.net/specs/) for comparison with the proposed document

It is written in python and has a ```requirements.txt``` which specifies 
pip libaries required for processesing.

## Options

```
Usage: python cli-tool.py [OPTIONS] [FILENAME]
Options:
Options:
  -filename-state   Analyze filename state
  -content-state    Analyze content state
  -content-date     Extract content date
  -date YYYY-MM-DD  Compare with a specific date (use with -content-date)
  -content-ref      Extract references
  -check-url        Check accessibility of URLs in references
  -content-notices  Check notices and copyright
  -content-struct   Check document structure
  -content-authors  Extract author information
  -content-history  Check for document history
  -content-title    Compare title in documents
  -content-filename-match  Check if content type and number match filename
  -process-draft FILE  Process a draft file and output file names
  -check-draft FILE Check if file already exists in spec-list.csv
  -list             List full document history (use with -content-history)
  -get-spec-list-csv Retrieve the spec list as CSV (default output: spec-list.csv)
  -output FILE      Specify custom output file for -get-spec-list-csv
  -get-specs        Download all specification files
  -directory DIR    Specify directory for downloaded specs (use with -get-specs)
  -debug            Show debug information (matched patterns)```

# process.sh
This is a tool for integration with [GitHub Actions](https://docs.github.com/en/actions)
for the automation of the submission of standards.

It assumes that the files to be processed match the submission form.
It assumes that the files to be processed are stored within a git repository.
It detects changed files using:
```
git diff --name-only origin/main...HEAD | grep '\.html$'
```

If no html files are added it exits
If html files are added to more than one WG sub directory it will fail

It iterates through the proposed new html files and performs a number of checks:
*   Check existence of document history when in "Draft" or "Implementers Draft"
*   Checks history is absent when "Final" or "Errata"
*  Check change file to see if it is already published at https://openid.net/specs
*  Confirm the existence of authors
*  Confirm the existence of notices for copyright and ownership
*  Confirm the existence of references and URLs accessibility
*  Confirm the structure of the document
   *   'ABSTRACT':
   *   'INTRODUCTION'
   *   'REFERENCES'
   *   'NORMATIVE_REFERENCES'
   *   'INFORMATIVE_REFERENCES'
   *   'ACKNOWLEDGEMENTS'
   *   'SECURITY`
*   Check the content state title matches the filename
* Checks publication date is within last 10 days
If any of these checks fail it exits with a returns a non-zero exit code


