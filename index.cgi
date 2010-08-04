#! /usr/bin/perl

use strict;
use warnings;

use FATE;

opendir D, $fatedir or fail 'Server error: $fatedir not found';
my @slots = grep /^[^.]/, readdir D;
closedir D;

my @reps;
my $allpass = 0;
my $allfail = 0;

for my $slot (@slots) {
    my $rep = load_summary $slot, 'latest' or next;
    push @reps, $rep;
    if ($$rep{npass} == 0) {
        $allfail++;
    } elsif ($$rep{npass} == $$rep{ntests}) {
        $allpass++;
    }

    if (my $prev = load_summary $slot, 'previous') {
        my $nfail = $$rep{ntests}  - $$rep{npass};
        my $pfail = $$prev{ntests} - $$prev{npass};
        $$rep{alert} = $$rep{ntests} && $nfail <=> $pfail;
    }
}

$allpass = int 100 * $allpass / @reps;
$allfail = int 100 * $allfail / @reps;
my $warn = int 100 - $allpass - $allfail;

print "Content-type: text/html\r\n\r\n";

doctype;
start 'html', xmlns => "http://www.w3.org/1999/xhtml";
start 'head';
tag 'meta', 'http-equiv' => "Content-Type",
            'content'    => "text/html; charset=utf-8";
tag 'link', rel  => 'stylesheet',
            type => 'text/css',
            href => 'fate.css';
print "<title>FATE</title>\n";
print <<EOF;
<script type="text/javascript">
  function toggle(id, arr) {
      var e = document.getElementById(id);
      if (e.style.display == 'table-row') {
          e.style.display = 'none';
          arr.textContent = '\\u25ba'
      } else {
          e.style.display = 'table-row';
          arr.textContent = '\\u25bc'
      }
  }
</script>
EOF
end 'head';

start 'body';
h1 'FATE';

start 'table', id => 'index', class => 'replist';
start 'thead';
start 'tr';
start 'td', colspan => 7, id => 'failometer';
span '&nbsp;', class => 'pass', style => "width: ${allpass}%";
span '&nbsp;', class => 'warn', style => "width: ${warn}%";
span '&nbsp;', class => 'fail', style => "width: ${allfail}%";
end 'td';
end 'tr';
start 'tr';
th 'Time';
th 'Arch';
th 'OS';
th 'Compiler';
th 'Rev';
th 'Result', colspan => 2;
end 'tr';
end 'thead';
start 'tbody';
for my $rep (sort { $$a{slot} cmp $$b{slot} } @reps) {
    my $ntest = $$rep{ntests};
    my $npass = $$rep{npass};
    my $time = parse_date $$rep{date};
    my $age  = time - $time;
    my $agestr = agestr $age, $time;
    my $ageclass = '';
    my $rtext;
    my $rclass;
    my $alert = ('rejoice', '', 'alert')[$$rep{alert} + 1];
    (my $slotid = $$rep{slot}) =~ s/[^a-z0-9_-]/_/ig;

    if ($age < $recent_age) {
        $ageclass = 'recent';
    } elsif ($age > $ancient_age) {
        $ageclass = 'ancient';
    }

    start 'tr', class => "$ageclass $alert alt hilight";
    start 'td';
    anchor $agestr, href => "history.cgi?slot=$$rep{slot}";
    end 'td';
    td $$rep{subarch} || $$rep{arch};
    td $$rep{os};
    td $$rep{cc};
    td $$rep{rev};
    if ($npass) {
        $rtext  = "$npass / $ntest";
        $rclass = $npass==$ntest? 'pass' : $npass? 'warn' : 'fail';
    } else {
        $rtext  = $$rep{errstr};
        $rclass = 'fail'
    }
    start 'td', class => $rclass;
    anchor $rtext, href => "report.cgi?slot=$$rep{slot}&amp;time=$$rep{date}";
    end 'td';
    start 'td', class => $rclass;
    if ($npass < $ntest) {
        span '&#9658;', class => 'toggle', onclick => "toggle('$slotid', this)";
    }
    end 'td';
    end 'tr';
    print "\n";
    if ($npass < $ntest) {
        my $report = load_report $$rep{slot}, $$rep{date};
        my @fail = grep $$_{status} ne '0', @{$$report{recs}};
        my $nfail = @fail;
        start 'tr', id => $slotid, class => 'slotfail';
        start 'td', colspan => 7;
        start 'table', class => 'minirep';
        start 'thead';
        start 'tr';
        th "$nfail failed tests";
        th 'Status', class => 'errcode';
        end 'tr';
        end 'thead';
        start 'tbody';
        for (sort { $$a{name} cmp $$b{name} } @fail) {
            start 'tr', class => 'alt hilight';
            td $$_{name};
            td $$_{status}, class => 'errcode';
            end 'tr';
        }
        end 'tbody';
        end 'table';
        end 'td';
        end 'tr';
        print "\n";
        trowa { style => 'display: none' }, '';
    }
}
end 'tbody';
end 'table';
end 'body';
end 'html';
