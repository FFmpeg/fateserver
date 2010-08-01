#! /bin/sh

set -e
export LC_ALL=C

die(){
    echo "$@"
    exit 1
}

test -n "$FATEDIR" || die "FATEDIR not set"
test -n "$FATE_USER" || die "FATE_USER not set"

reptmp=$(mktemp -d)
trap 'rm -r $reptmp' EXIT
cd $reptmp

tar xzk

header=$(head -n1 report)
date=$(expr "$header" : 'fate:0:\([0-9]*\):')
slot=$(expr "$header" : 'fate:0:[0-9]*:\([A-Za-z0-9_.-]*\):')
rev=$(expr "$header" : "fate:0:$date:$slot:\([A-Za-z0-9_.-]*\):")

test -n "$date" && test -n "$slot" || die "Invalid report header"

slotdir=$FATEDIR/$slot

if [ -d "$slotdir" ]; then
    owner=$(cat "$slotdir/owner")
    test "$owner" = "$FATE_USER" || die "Slot $slot owned by somebody else"
else
    mkdir "$slotdir"
    echo "$FATE_USER" >"$slotdir/owner"
fi

exec <report
head -n2 >summary

ntest=0
npass=0
IFS=:

exec >pass
while read name status rest; do
    if [ "$status" = 0 ]; then
        echo "$name:$date:$rev"
        npass=$(($npass+1))
    fi
    ntest=$(($ntest+1))
done
exec <&- >&-

upass(){
    read pname pdate prev
    while read lname ldate lrev; do
        test "$lname" != "$pname" && echo "$pname:$pdate:$prev"
        pname=$lname
        pdate=$ldate
        prev=$lrev
    done
    echo "$pname:$pdate:$prev"
}

lastpass=$slotdir/lastpass

if [ -r $lastpass ]; then
    sort pass $lastpass | upass >lastpass
else
    sort -o lastpass pass
fi

unset IFS

echo "stats:$ntest:$npass" >>summary

repdir=$slotdir/$date
mkdir $repdir
gzip -9 *.log
xz report
cp -p summary report.xz *.log.gz $repdir
rm -f $slotdir/previous
test -e $slotdir/latest && mv $slotdir/latest $slotdir/previous
ln -s $date $slotdir/latest
cp lastpass ${lastpass}.new && mv ${lastpass}.new $lastpass
