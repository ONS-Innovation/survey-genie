#!/bin/sh

set -e

TMPFILE=`mktemp ./templates.XXXXXXXXXX`

wget https://github.com/ONSdigital/design-system/releases/download/72.1.2/templates.zip -O $TMPFILE
rm -rf survey_genie/templates/components
rm -rf survey_genie/templates/layout

unzip -d ./survey_genie $TMPFILE
rm $TMPFILE