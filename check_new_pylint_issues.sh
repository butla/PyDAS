#!/bin/bash

# this script must run after Pylint run
REMOTE_MASTER=origin/master

# If there's no difference between the current state and origin/master
# then there's no need to check for new Pylint issues.
if [[ -z $(git diff $REMOTE_MASTER) ]]; then
    exit
fi

# If there are working directory changes then we'll need to stash them and pop later.
STASH_NEEDED=false
if [[ $(git diff HEAD) ]]; then
    STASH_NEEDED=true
    git stash &>/dev/null
fi

CURRENT_BRANCH=$(git branch | grep "*" | cut -c3-)
CURRENT_ISSUES=$(cat pylint_report.txt | wc -l)

# go check up on the old issues
git checkout $REMOTE_MASTER &>/dev/null
OLD_ISSUES=$(pylint data_acquisition | wc -l)

# restore the working tree
git checkout $CURRENT_BRANCH &>/dev/null
if $STASH_NEEDED ; then
    git stash pop &>/dev/null
fi

ISSUE_DIFF=$(($CURRENT_ISSUES - $OLD_ISSUES))
if [ $ISSUE_DIFF -lt 0 ]; then
    echo "Changes decrease the number of issues by $(($ISSUE_DIFF * -1)). Great! :)"
else
    echo "New Pylint issues found: $ISSUE_DIFF"
    exit $ISSUE_DIFF
fi