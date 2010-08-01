#! /usr/bin/perl

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
my %lastpass;

while (<R>) {
    my $rec = split_rec $_;
    ${$$rec{status}? \%fail: \%pass}{$$rec{name}} = $rec;
}

close R;

my $npass = keys %pass;
my $nfail = keys %fail;
my $ntest = $npass + $nfail;

if (open P, "$slotdir/lastpass") {
    while (<P>) {
        my ($test, $pdate, $prev) = split /:/;
        $lastpass{$test} = { date => $pdate, rev => $prev };
    }
    close P;
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
            href => 'fate.css';
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
trow 'Compiler',      $$conf{cc};
trow 'Configuration', $$conf{config};
trow 'Revision',      $$hdr{rev};
trow 'Date',          asctime gmtime parse_date $$hdr{date};
trow 'Status',        $npass? "$npass / $ntest" : $$hdr{errstr};
start 'tr';
td 'Logs';
start 'td';
while (my $logfile = glob "$repdir/*.log.gz") {
    my ($log) = $logfile =~ m!^$repdir/([a-z_.-]+)\.log\.gz$! or next;
    anchor $log, href => "log.cgi?slot=$$hdr{slot}&amp;time=$$hdr{date}&amp;log=$log";
    print "\n";
}
end 'td';
end 'tr';
end;

start 'table', id => 'tests', class => 'replist';
if ($nfail) {
    start 'tr', class => 'fail';
    th "$nfail failed tests", colspan => 3;
    th 'Status', class => 'errcode';
    th 'Last good rev', class => 'lastpass';
    end 'tr';
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
        td $lastpass{$n}? $lastpass{$n}{rev} : 'n / a';
        end 'tr';
        start 'tr', id => "$test-diff", class => 'diff';
        td $diff, colspan => 5;
        end 'tr';
        start 'tr', id => "$test-err",  class => 'diff';
        td $err,  colspan => 5;
        end 'tr';
    }
} elsif ($ntest) {
    start 'tr'; th 'All tests successful', colspan => 3, class => 'pass'; end;
} else {
    start 'tr'; th 'No tests were run',    colspan => 3, class => 'fail'; end;
}
end 'table';

end 'body';
end 'html';
