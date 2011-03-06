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

use POSIX qw/asctime/;
use CGI qw/param/;
use HTML::Entities;
use MIME::Base64;
use FATE;

my $req_slot = param 'slot';
my $req_time = param 'time';

my $slotdir = "$fatedir/$req_slot";
my $repdir = "$slotdir/$req_time";
my $report = "$repdir/report.xz";

open R, '-|', "unxz -c $report" or fail 'Requsted report not found';

my $hdr  = split_header scalar <R> or fail 'Invalid report';
my $conf = split_config scalar <R> or fail 'Invalid report';
$$hdr{version} eq '0'              or fail 'Bad report version';

my %pass;
my %fail;

while (<R>) {
    my $rec = split_rec $_;
    ${$$rec{status}? \%fail: \%pass}{$$rec{name}} = $rec;
}

close R;

my $npass = keys %pass;
my $nfail = keys %fail;
my $ntest = $npass + $nfail;

my $rep = load_summary $req_slot, $req_time;
my $lastpass = load_lastpass $req_slot;

my $owner;
if (open O, "$slotdir/owner") {
    chomp($owner = <O>);
    close O;
}

# main text

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
print "<title>FATE: $$hdr{slot} $$hdr{rev}</title>\n";
print <<EOF;
<script type="text/javascript">
  function toggle(id) {
      var e = document.getElementById(id);
      e.style.display = e.style.display == 'table-row' ? 'none' : 'table-row';
  }
  function hide(id) {
      var e = document.getElementById(id);
      e.style.display = 'none';
  }
  function show_diff(name) {
      hide(name + '-err');
      toggle(name + '-diff');
  }
  function show_err(name) {
      hide(name + '-diff');
      toggle(name + '-err');
  }
</script>
EOF
end 'head';

start 'body';
h1 "$$hdr{slot} $$hdr{rev}", id => 'title';

start 'table', id => 'config';
trow 'Architecture',  $$conf{arch};
trow 'Variant',       $$conf{subarch};
trow 'CPU',           $$conf{cpu};
trow 'OS',            $$conf{os};
trow 'Owner',         $owner if $owner;
trow 'Compiler',      $$conf{cc};
trow 'Configuration', $$conf{config};
start 'tr';
td   'Revision';
if ($gitweb and $$hdr{rev} =~ /git-(.*)/) {
    start 'td';
    anchor $$hdr{rev}, href => "$gitweb;a=commit;h=$1";
    end 'td';
} else {
    td $$hdr{rev};
}
end 'tr';
trow 'Date',          asctime gmtime parse_date $$hdr{date};
trow 'Status',        $npass? "$npass / $ntest" : "$$hdr{errstr} ($$hdr{status})";
trow 'Warnings',      $$rep{nwarn};
start 'tr';
td 'Logs';
start 'td';
while (my $logfile = glob "$repdir/*.log.gz") {
    my ($log) = $logfile =~ m!^$repdir/([a-z_.-]+)\.log\.gz$! or next;
    anchor $log, href => href slot=>$$hdr{slot}, time=>$$hdr{date}, log=>$log;
    print "\n";
}
end 'td';
end 'tr';
end;

start 'table', id => 'tests', class => 'replist';
if ($nfail) {
    start 'thead';
    start 'tr', class => 'fail';
    th "$nfail failed tests", colspan => 3;
    th 'Status', class => 'errcode';
    th 'Last good rev', class => 'lastpass';
    end 'tr';
    end 'thead';
    start 'tbody';
    for my $n (sort keys %fail) {
        my $rec = $fail{$n};
        my $test = $$rec{name};
        my $diff = encode_entities decode_base64($$rec{diff}), '<>&"';
        my $err  = encode_entities decode_base64($$rec{stderr}), '<>&"';
        if ($diff =~ /^--- /) {
            $diff =~ s!^--- .*$!<span class="diff-old">$&</span>!gm;
            $diff =~ s!^\+\+\+ .*$!<span class="diff-new">$&</span>!gm;
            $diff =~ s!^\@\@.*\@\@.*$!<span class="diff-hnk">$&</span>!gm;
            $diff =~ s!^-.*$!<span class="diff-del">$&</span>!gm;
            $diff =~ s!^\+.*$!<span class="diff-add">$&</span>!gm;
            $diff =~ s!^ .*$!<span class="diff-nop">$&</span>!gm;
        }
        if ($diff =~ /^\s*$/) {
            $diff = '<em>No diff output recorded</em>';
        }
        start 'tr', class => 'alt hilight';
        td "diff",    class => 'toggle', onclick => "show_diff('$test')";
        td "stderr",  class => 'toggle', onclick => "show_err('$test')";
        td $test;
        td $$rec{status}, class => 'errcode';
        if ($$lastpass{$n} and $gitweb) {
            my ($old, $new);
            $$lastpass{$n}{rev} =~ /git-(.*)/ and $old = $1;
            $$hdr{rev}         =~ /git-(.*)/ and $new = $1;
            if ($old and $new) {
                start 'td';
                anchor $$lastpass{$n}{rev}, href => "$gitweb;a=shortlog;h=$new;hp=$old";
                end 'td';
            } else {
                td $$lastpass{$n}{rev};
            }
        } else {
            td $$lastpass{$n}? $$lastpass{$n}{rev} : 'n / a';
        }
        end 'tr';
        start 'tr', id => "$test-diff", class => 'diff';
        td $diff, colspan => 5;
        end 'tr';
        start 'tr', id => "$test-err",  class => 'diff';
        td $err,  colspan => 5;
        end 'tr';
    }
    end 'tbody';
} elsif ($ntest) {
    start 'tr'; th 'All tests successful', colspan => 3, class => 'pass'; end;
} else {
    start 'tr'; th 'No tests were run',    colspan => 3, class => 'fail'; end;
}
end 'table';

end 'body';
end 'html';
