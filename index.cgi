#! /usr/bin/perl
#
# Copyright (c) 2011 Mans Rullgard <mans@mansr.com>
# Copyright (c) 2014 Tiancheng "Timothy" Gu <timothygu99@gmail.com>
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
use URI::Escape;

# Format for /?query= : /?query=type:value//type:value// (URI encoded).
# Trailing // does not matter (i.e. may be added).
# @queries contains an array of 'type:value' strings.
# Every member of @queries can be further parsed with another simple
# split(/:/, $this_query, 2);
my @queries = split(/\/\//, uri_unescape param 'query') if (param 'query');

my $sort = param('sort');
$sort =~ s/[^A-Za-z0-9 ]*//g;
param('sort', $sort);
$sort    = $sort eq 'arch' ? 'subarch': $sort;

(my $uri = $ENV{REQUEST_URI}) =~ s/\?.*//;

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

    my $not_matched = 0;
    $$rep{subarch} = $$rep{arch} if not $$rep{subarch};
    for my $this_query (@queries) {
        my ($type, $text) = split(/:/, $this_query, 2);
        $not_matched = 1 if ($$rep{$type} ne $text);
    }
    next if $not_matched;

    push @reps, $rep;
    if ($$rep{npass} == $$rep{ntests} and !$$rep{status}) {
        $allpass++;
    } elsif ($$rep{npass} == 0) {
        $allfail++;
    }

    if (my $prev = load_summary $slot, 'previous') {
        my $pfail = $$prev{ntests} - $$prev{npass};
        $$rep{alert} = $$rep{ntests} && $$rep{nfail} <=> $pfail;
        $$rep{dwarn} = $$rep{nwarn} <=> $$prev{nwarn};
        $$rep{pdate} = $$prev{date};
    }
}

@reps or fail @queries ? 'No items matching search criteria. ' .
                         "<a href=\"$uri\">Clear all search criteria.</a>" :
                         'No data in $fatedir.';

$allpass = 100 * $allpass / @reps;
$allfail = 100 * $allfail / @reps;
my $warn = 100 - $allpass - $allfail;

my @sort = ('subarch', 'os', 'cc', 'comment', 'slot');
my $sdir = 1; # default to ascending sorting
defined $sort and unshift @sort, split /\/\//, $sort;
$sort ||= $sort[0];

sub nscmp {
    my ($a, $b) = @_;
    return int $a || int $b ? $a <=> $b : lc $a cmp lc $b;
}

sub repcmp {
    my $r;
    for my $s (@sort) {
        if ($s =~ /^desc/) {
            $s =~ s/^desc//;
            $sdir = -1;
        }
        last if $r = $sdir * nscmp $$a{$s}, $$b{$s};
    }
    return $r;
};

sub lsort {
    my $params = '';
    for my $thisparam (param) {
        next if $thisparam =~ 'sort';
        $params .= '&' if $params ne '';
        $params .= "$thisparam=" . param($thisparam);
    }
    $params .= '&' if $params;
    my ($text, $key) = @_;

    my $newkey = '';
    if ($sort eq $key) {                           # $key     = $sort
        for my $thiskey (split /\/\//, $key) {
            if ($thiskey =~ /^desc/) {             # $thiskey = desc*
                $thiskey =~ s/^desc//;
            } else {                               # $thiskey = *
                $thiskey = "desc$thiskey";
            }
            if ($newkey eq '') {
                $newkey = $thiskey;
            } else {
                $newkey .= "//$thiskey";
            }
        }
    }

    $key = $newkey if $newkey ne '';
    anchor $text, href => "$uri?${params}sort=$key";
}

sub category {
    my ($category, $rep) = @_;
    my $head_printed = 0;

    # $params will contain parameters else than query, if any, in HTTP format.
    my $params = '';
    for my $thisparam (param) {
        next if $thisparam eq 'query';
        $params .= '&' if $params ne '';
        $params .= "$thisparam=" . param($thisparam);
    }
    my $head = ($params ? '&' : '') . 'query=';

    if (@queries) {
        for my $this_query (@queries) {
            my ($type, $text) = split(/:/, $this_query, 2);
            if ($type ne $category) {
                $params .= $head if (!$head_printed);
                $params .= $this_query . '//';
                $head_printed = 1;
            }
        }
    }
    $params .= $head if (!$head_printed);
    $params .= "$category:" . uri_escape_utf8 "$$rep{$category}" . '//';
    $head_printed = 1;                 # for the sake of completeness

    start 'td';
    anchor $$rep{$category}, href => "$uri?$params";
    end 'td';
}

print "Content-type: text/html\r\n";
print "Access-Control-Allow-Origin: https://ffmpeg.org\r\n";

if ($ENV{HTTP_ACCEPT_ENCODING} =~ /gzip/) {
    print "Content-Encoding: gzip\r\n\r\n";
    open STDOUT, '|-', 'gzip';
} else {
    print "\r\n";
}

head1;
print "<title>FATE</title>\n";
print <<EOF;
<script type="text/javascript">
  function toggle(id, arr) {
      var e = document.getElementById(id);
      if (e.style.display == 'table-row') {
          e.style.display = 'none';
          arr.classList.remove("fa-caret-up");
          arr.classList.add("fa-caret-down");
      } else {
          e.style.display = 'table-row';
          arr.classList.add("fa-caret-up");
          arr.classList.remove("fa-caret-down");
      }
  }
</script>
EOF
head2;
print "FATE\n";
head3;

if (@queries) {
    start 'p';
    print 'Search patterns: ';
    for my $this_query (@queries) {
        my ($type, $text) = split(/:/, $this_query, 2);
        print "$type: $text; ";
    }
    anchor 'clear all.', href => "$uri";
    end 'p';
}

start 'div', class => 'table-responsive';
start 'table', id => 'index', class => 'replist table';
start 'thead';
start 'tr';
start 'td', colspan => 8, id => 'failometer';
start 'div', class => 'progress';
if ($allpass) {
    print <<EOF;
<div class="progress-bar pass" role="progressbar" title="${allpass}% tests passed" aria-valuenow="${allpass}" aria-valuemin="0" aria-valuemax="100" style="width: ${allpass}%">
  <span class="sr-only">${allpass}%</span>
</div>
EOF
}
if ($warn) {
    print <<EOF;
<div class="progress-bar warn" role="progressbar" title="${warn}% tests failed" aria-valuenow="${warn}" aria-valuemin="0" aria-valuemax="100" style="width: ${warn}%">
  <span class="sr-only">${warn}%</span>
</div>
EOF
}
if ($allfail) {
    print <<EOF;
<div class="progress-bar fail" role="progressbar" title="${allfail}% build failed" aria-valuenow="${allfail}" aria-valuemin="0" aria-valuemax="100" style="width: ${allfail}%">
  <span class="sr-only">${allfail}%</span>
</div>
EOF
}
end 'div';
end 'td';
end 'tr';
start 'tr';
start 'th'; lsort 'Time',     'descdate';      end 'th';
start 'th'; lsort 'Rev',      'rev';           end 'th';
start 'th'; lsort 'Arch',     'arch';          end 'th';
start 'th'; lsort 'OS',       'os';            end 'th';
start 'th'; lsort 'Compiler', 'cc';            end 'th';
start 'th'; lsort 'Comment',  'comment';       end 'th';
start 'th'; lsort 'Warnings', 'nwarn';         end 'th';
start 'th'; lsort 'Tests',    'npass';         end 'th';
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
    my $alert = ('pass', '', 'warn')[$$rep{alert} + 1];
    my $walert = ('pass', '', 'warn')[$$rep{dwarn} + 1];
    (my $slotid = $$rep{slot}) =~ s/[^a-z0-9_-]/_/ig;

    if ($age < $recent_age) {
        $ageclass = 'recent';
    } elsif ($age > $ancient_age) {
        $ageclass = 'ancient';
        $alert = '';
    }

    start 'tr', class => "$ageclass $alert";
    start 'td';
    anchor $agestr, href => href slot => $$rep{slot};
    end 'td';
    if ($gitweb and $$rep{rev} =~ /(N-)?(.*)/) {
        start 'td';
        anchor $$rep{rev}, href => "$gitweb;a=commit;h=$2";
        end 'td';
    } else {
        td $$rep{rev};
    }

    category 'subarch', $rep;
    category 'os', $rep;
    category 'cc', $rep;
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
    start 'td', class => "$walert";
    start 'div', class => 'pull-left';
    anchor $$rep{nwarn},
        href => href slot => $$rep{slot}, time => $$rep{date}, log => 'compile';
    end;
    start 'div', class => 'pull-right';
    anchor '±',
        href => href slot => $$rep{slot}, time => $$rep{date},
        log => "compile/$$rep{pdate}";
    end;
    end;
    start 'td', class => "$rclass";
    start 'div', class => 'pull-left';
    anchor $rtext, href => href slot => $$rep{slot}, time => $$rep{date};
    end;
    if ($npass < $ntest or $log) {
        start 'div', class => 'pull-right';
        span '', class => 'toggle fa fa-caret-down', onclick => "toggle('$slotid', this)";
        end;
    }
    end;
    end 'tr';
    print "\n";
    if ($npass < $ntest && $ntest - $npass < 100) {
        trowa { style => 'display: none' }, '';
        print "\n";
        my $report = load_report $$rep{slot}, $$rep{date};
        my @fail = grep $$_{status} ne '0', @{$$report{recs}};
        my $lastpass = load_lastpass $$rep{slot};

        start 'tr', id => $slotid, class => 'slotfail';
        start 'td', colspan => 8;
        start 'table', class => 'minirep';
        start 'thead';
        start 'tr';
        if ($$rep{nfail} eq 1) {
            th "1 failed test";
        } else {
            th "$$rep{nfail} failed tests";
        }
        th 'Status', class => 'errcode';
        end 'tr';
        end 'thead';
        start 'tbody';
        for (sort { $$a{name} cmp $$b{name} } @fail) {
            my $falert = $$rep{pdate} eq $$lastpass{$$_{name}}{date} ?
              'warn' : '';
            start 'tr', class => "$falert";
            td $$_{name};
            td $$_{status}, class => 'errcode';
            end 'tr';
        }
        end 'tbody';
        end 'table';
        end 'td';
        end 'tr';
        print "\n";
    } elsif ($log) {
        trowa { style => 'display: none' }, '';
        start 'tr', id => $slotid, class => 'slotfail';
        start 'td', colspan => 8;
        start 'pre', class => 'minilog';
        print encode_entities($log, '<>&"');
        end 'pre';
        end 'td';
        end 'tr';
    }
}
end 'tbody';
end 'table';
end 'div';
footer;
