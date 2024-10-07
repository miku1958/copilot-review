#!/bin/zsh

SCRIPT_DIR=$(dirname "$0")
staged_files=$(git diff --cached --name-only)

for file in $staged_files; do
    if [[ 
        "$file" != *.swift &&
        "$file" != *.m &&
        "$file" != *.mm &&
        "$file" != *.h &&
        "$file" != *.c &&
        "$file" != *.cpp &&
        "$file" != *.ts ]] \
        ; then
        continue
    fi
    diffContent=$(git diff --cached --unified=1 "$file" | awk '{gsub(/\\/, "\\\\"); gsub(/"/, "\\u0022"); gsub(/\t/, "\\t"); printf "%s\\n", $0}')
    diffArray=()
    currentDiff=""
    while IFS= read -r line; do
        if [[ $line =~ ^@@ ]]; then
            if [[ -n $currentDiff ]]; then
                diffArray+=("$currentDiff")
            fi
            currentDiff="$line"
        else
            currentDiff+=$'\n'"$line"
        fi
    done <<<"$(echo "$diffContent" | awk '/^@@/ {if (NR!=1) print ""; print} !/^@@/ {print}' RS=)"
    if [[ -n $currentDiff ]]; then
        diffArray+=("$currentDiff")
    fi
    filteredArray=()
    for element in "${diffArray[@]}"; do
        if [[ $element =~ ^@@ ]]; then
            filteredArray+=("$element")
        fi
    done
    for element in "${filteredArray[@]}"; do
        python3 $SCRIPT_DIR/api.py "$element"

        echo "-----------------------------------------------"
        echo "-----------------------------------------------"
        echo "-----------------------------------------------"
    done
done
