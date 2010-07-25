#! /bin/sh

set -e

die(){
    echo "$@"
    exit 1
}

fatedir=/tmp/fate-reports

reptmp=$(mktemp -d)
trap 'rm -r $reptmp' EXIT
cd $reptmp

tar xz

header=$(head -n1 report)
date=$(expr "$header" : 'fate:0:\([0-9]*\)')
slot=$(expr "$header" : 'fate:0:[0-9]*:\([^:]*\)')

test -n "$date" && test -n "$slot" || die "Invalid report header"

slotdir=$fatedir/$slot

if [ -d "$slotdir" ]; then
    owner=$(cat "$slotdir/owner")
    test "$owner" = "$FATE_USER" || die "Slot $slot owned by somebody else"
else
    mkdir "$slotdir"
    echo "$FATE_USER" >"$slotdir/owner"
fi

repdir=$slotdir/$date
mkdir $repdir
cp -p report *.log $repdir
rm -f $slotdir/latest
ln -s $date $slotdir/latest
