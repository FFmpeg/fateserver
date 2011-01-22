#! /usr/bin/perl

use strict;
use warnings;

use CGI qw/param/;
use HTML::Entities;
use FATE;

opendir D, $fatedir or fail 'Server error: $fatedir not found';
my @slots = grep /^[^.]/, readdir D;
closedir D;

my @reps;
my $allpass = 0;
my $allfail = 0;

for my $slot (@slots) {
    next if -e "$fatedir/$slot/hidden";
    my $rep = load_summary $slot, 'latest' or next;
    next if time - parse_date($$rep{date}) > $hidden_age;
    $$rep{subarch} = $$rep{arch} if not $$rep{subarch};
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

$allpass = 100 * $allpass / @reps;
$allfail = 100 * $allfail / @reps;
my $warn = 100 - $allpass - $allfail;

my @sort = ('subarch', 'os', 'cc', 'slot');
my $sort = param('asort') || param('dsort');
my $sdir = param('dsort') ? -1 : 1;
defined $sort and unshift @sort, $sort eq 'arch'? 'subarch': $sort;
$sort ||= $sort[0];

sub repcmp {
    my $r;
    for my $s (@sort) {
        last if $r = $sdir * (lc $$a{$s} cmp lc $$b{$s});
    }
    return $r;
};

(my $uri = $ENV{REQUEST_URI}) =~ s/\?.*//;
my $params = join '&', map param($_), grep $_ !~ 'sort', param;
$params .= '&' if $params;

sub lsort {
    my ($text, $key, $p) = @_;
    if ($sort eq $key) {
        $p = param('asort') ? 'dsort' : 'asort';
    }
    if (!$p) {
        $p = 'asort';
    }
    anchor $text, href => "$uri?$params$p=$key";
}

print "Content-type: text/html\r\n";

if ($ENV{HTTP_ACCEPT_ENCODING} =~ /gzip/) {
    print "Content-Encoding: gzip\r\n\r\n";
    open STDOUT, '|-', 'gzip';
} else {
    print "\r\n";
}

doctype;
start 'html', xmlns => "http://www.w3.org/1999/xhtml";
start 'head';
tag 'meta', 'http-equiv' => "Content-Type",
            'content'    => "text/html; charset=utf-8";
tag 'link', rel  => 'stylesheet',
            type => 'text/css',
            href => '/fate.css';
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
span '&nbsp;', class => 'pass', style => "width: ${allpass}%" if $allpass;
span '&nbsp;', class => 'warn', style => "width: ${warn}%"    if $warn;
span '&nbsp;', class => 'fail', style => "width: ${allfail}%" if $allfail;
end 'td';
end 'tr';
start 'tr';
start 'th'; lsort 'Time',     'date', 'dsort'; end 'th';
start 'th'; lsort 'Arch',     'arch';          end 'th';
start 'th'; lsort 'OS',       'os';            end 'th';
start 'th'; lsort 'Compiler', 'cc';            end 'th';
start 'th'; lsort 'Rev',      'rev';           end 'th';
start 'th', colspan => 2; lsort 'Result', 'npass'; end 'th';
end 'tr';
end 'thead';
start 'tbody';
for my $rep (sort repcmp @reps) {
    my $ntest = $$rep{ntests};
    my $npass = $$rep{npass};
    my $time = parse_date $$rep{date};
    my $age  = time - $time;
    my $agestr = agestr $age, $time;
    my $ageclass = '';
    my $rtext;
    my $rclass;
    my $log;
    my $alert = ('rejoice', '', 'alert')[$$rep{alert} + 1];
    (my $slotid = $$rep{slot}) =~ s/[^a-z0-9_-]/_/ig;

    if ($age < $recent_age) {
        $ageclass = 'recent';
    } elsif ($age > $ancient_age) {
        $ageclass = 'ancient';
    }

    start 'tr', class => "$ageclass $alert alt hilight";
    start 'td';
    anchor $agestr, href => href slot => $$rep{slot};
    end 'td';
    td $$rep{subarch};
    td $$rep{os};
    td $$rep{cc};
    if ($gitweb and $$rep{rev} =~ /git-(.*)/) {
        start 'td';
        anchor $$rep{rev}, href => "$gitweb;a=commit;h=$1";
        end 'td';
    } else {
        td $$rep{rev};
    }
    if ($npass) {
        $rtext  = "$npass / $ntest";
        $rclass = $npass==$ntest? 'pass' : $npass? 'warn' : 'fail';
    } else {
        $rtext  = $$rep{errstr};
        $rclass = 'fail';
        for my $base ('test', 'compile', 'configure') {
            my $file = "$fatedir/$$rep{slot}/$$rep{date}/$base.log.gz";
            if (-r $file) {
                $log = qx{zcat $file | tail -n20};
                last;
            }
        }
    }
    start 'td', class => "$rclass resleft";
    anchor $rtext, href => href slot => $$rep{slot}, time => $$rep{date};
    end 'td';
    start 'td', class => "$rclass resright";
    if ($npass < $ntest or $log) {
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
    } elsif ($log) {
        start 'tr', id => $slotid, class => 'slotfail';
        start 'td', colspan => 7;
        start 'pre', class => 'minilog';
        print encode_entities($log, '<>&"');
        end 'pre';
        end 'td';
        end 'tr';
        trowa { style => 'display: none' }, '';
    }
}
end 'tbody';
end 'table';
end 'body';
end 'html';
