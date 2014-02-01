#! /usr/bin/perl
#
# Copyright (c) 2011 Mans Rullgard <mans@mansr.com>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHORS DISCLAIM ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

use strict;
use warnings;

use CGI qw/param/;
use HTML::Entities;
use FATE;
use Time::Zone;

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
    if ($$rep{npass} == $$rep{ntests} and !$$rep{status}) {
        $allpass++;
    } elsif ($$rep{npass} == 0) {
        $allfail++;
    }

    if (my $prev = load_summary $slot, 'previous') {
        my $nfail = $$rep{ntests}  - $$rep{npass};
        my $pfail = $$prev{ntests} - $$prev{npass};
        $$rep{alert} = $$rep{ntests} && $nfail <=> $pfail;
        $$rep{dwarn} = $$rep{nwarn} <=> $$prev{nwarn};
        $$rep{pdate} = $$prev{date};
    }
}

$allpass = 100 * $allpass / @reps;
$allfail = 100 * $allfail / @reps;
my $warn = 100 - $allpass - $allfail;

my @sort = ('subarch', 'os', 'cc', 'comment', 'slot');
my $sort = param('asort') || param('dsort');
my $sdir = param('dsort') ? -1 : 1;
defined $sort and unshift @sort, $sort eq 'arch'? 'subarch': $sort;
$sort ||= $sort[0];

sub nscmp {
    my ($a, $b) = @_;
    return int $a || int $b ? $a <=> $b : lc $a cmp lc $b;
}

sub repcmp {
    my $r;
    for my $s (@sort) {
        last if $r = $sdir * nscmp $$a{$s}, $$b{$s};
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
            href => '//ffmpeg.org/default.css';
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
          arr.textContent = '\\u25b6'
      } else {
          e.style.display = 'table-row';
          arr.textContent = '\\u25bc'
      }
  }
</script>
EOF
end 'head';

start 'body';
start 'div', id => 'container';

navbar;

start 'div', id => 'body';

h1 'FATE';

start 'table', id => 'index', class => 'replist';
start 'thead';
start 'tr';
start 'td', colspan => 10, id => 'failometer';
span '&nbsp;', class => 'pass', style => "width: ${allpass}%" if $allpass;
span '&nbsp;', class => 'warn', style => "width: ${warn}%"    if $warn;
span '&nbsp;', class => 'fail', style => "width: ${allfail}%" if $allfail;
end 'td';
end 'tr';
start 'tr';
start 'th'; lsort 'Time',     'date', 'dsort'; end 'th';
start 'th'; lsort 'Rev',      'rev';           end 'th';
start 'th'; lsort 'Arch',     'arch';          end 'th';
start 'th'; lsort 'OS',       'os';            end 'th';
start 'th'; lsort 'Compiler', 'cc';            end 'th';
start 'th'; lsort 'Comment',  'comment';       end 'th';
start 'th', colspan => 2; lsort 'Warnings', 'nwarn'; end 'th';
start 'th', colspan => 2; lsort 'Tests', 'npass'; end 'th';
end 'tr';
end 'thead';
start 'tbody';
for my $rep (sort repcmp @reps) {
    my $ntest = $$rep{ntests};
    my $npass = $$rep{npass};
    my $time = parse_date $$rep{date};
    my $age  = time - tz_local_offset() - $time;
    my $agestr = agestr $age, $time;
    my $ageclass = '';
    my $rtext;
    my $rclass;
    my $log;
    my $alert = ('rejoice', '', 'alert')[$$rep{alert} + 1];
    my $walert = ('rejoice', '', 'alert')[$$rep{dwarn} + 1];
    (my $slotid = $$rep{slot}) =~ s/[^a-z0-9_-]/_/ig;

    if ($age < $recent_age) {
        $ageclass = 'recent';
    } elsif ($age > $ancient_age) {
        $ageclass = 'ancient';
        $alert = '';
    }

    start 'tr', class => "$ageclass $alert alt hilight";
    start 'td';
    anchor $agestr, href => href slot => $$rep{slot};
    end 'td';
    if ($gitweb and $$rep{rev} =~ /(git-)?(.*)/) {
        start 'td';
        anchor $$rep{rev}, href => "$gitweb;a=commit;h=$2";
        end 'td';
    } else {
        td $$rep{rev};
    }
    td $$rep{subarch};
    td $$rep{os};
    td $$rep{cc};
    td $$rep{comment}, class => 'comment';
    if ($npass) {
        $rtext  = "$npass / $ntest";
        $rclass = $npass==$ntest? 'pass' : $npass? 'warn' : 'fail';
    } elsif (!$ntest and !$$rep{status}) {
        $rtext  = "build only";
        $rclass = $$rep{status}? 'fail' : 'pass';
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
    start 'td', class => 'warnleft';
    anchor $$rep{nwarn}, class => $walert,
      href => href slot => $$rep{slot}, time => $$rep{date}, log => 'compile';
    end;
    start 'td', class => 'warnright';
    anchor '±', class => $walert,
      href => href slot => $$rep{slot}, time => $$rep{date},
        log => "compile/$$rep{pdate}";
    end;
    start 'td', class => "$rclass resleft";
    anchor $rtext, href => href slot => $$rep{slot}, time => $$rep{date};
    end 'td';
    start 'td', class => "$rclass resright";
    if ($npass < $ntest or $log) {
        span '&#9654;', class => 'toggle', onclick => "toggle('$slotid', this)";
    }
    end 'td';
    end 'tr';
    print "\n";
    if ($npass < $ntest && $ntest - $npass < 100) {
        my $report = load_report $$rep{slot}, $$rep{date};
        my @fail = grep $$_{status} ne '0', @{$$report{recs}};
        my $nfail = @fail;
        my $lastpass = load_lastpass $$rep{slot};

        start 'tr', id => $slotid, class => 'slotfail';
        start 'td', colspan => 10;
        start 'table', class => 'minirep';
        start 'thead';
        start 'tr';
        if ($nfail eq 1) {
            th "$nfail failed test";
        } else {
            th "$nfail failed tests";
        }
        th 'Status', class => 'errcode';
        end 'tr';
        end 'thead';
        start 'tbody';
        for (sort { $$a{name} cmp $$b{name} } @fail) {
            my $falert = $$rep{pdate} eq $$lastpass{$$_{name}}{date} ?
              'alert' : '';
            start 'tr', class => "alt hilight $falert";
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
        start 'td', colspan => 10;
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
end 'div';
end 'div';
end 'body';
end 'html';
