#! /usr/bin/perl

use strict;
use warnings;

use CGI qw/param/;
use FATE;

our $fatedir;
require "$ENV{FATEWEB_CONFIG}";

my $slot = param 'slot';
my $slotdir = "$fatedir/$slot";

opendir D, $slotdir or fail "Slot $slot not found";
my @reps = grep { /^[0-9]/ and -d "$slotdir/$_" } readdir D;
close D;

print "Content-type: text/html\r\n\r\n";

doctype;
start 'html', xmlns => "http://www.w3.org/1999/xhtml";
start 'head';
tag 'meta', 'http-equiv' => "Content-Type",
            'content'    => "text/html; charset=utf-8";
tag 'link', rel  => 'stylesheet',
            type => 'text/css',
            href => 'fate.css';
print "<title>FATE: $slot</title>\n";
end 'head';

start 'body';
h1 "Report history for $slot";

start 'table', id => 'index';
trowh 'Time', 'Arch', 'OS', 'Compiler', 'Rev', 'Result';
for my $rep (sort { $b cmp $a } @reps) {
    open R, "$slotdir/$rep/report";
    my @header = split /:/, scalar <R>;
    my @config = split /:/, scalar <R>;
    my ($date, $slot, $rev, $err, $errstr) = @header[2..6];
    my ($arch, $subarch, $cpu, $os, $cc) = @config[1..5];
    my $ntest = 0;
    my $npass = 0;
    my $rtext;
    my $rclass;
    while (<R>) {
        my @rec = split /:/;
        $rec[1] == 0 and $npass++;
        $ntest++;
    }
    close R;
    start 'tr';
    td $date;
    td $subarch || $arch;
    td $os;
    td $cc;
    td $rev;
    if ($npass) {
        $rtext  = "$npass / $ntest";
        $rclass = $npass==$ntest? 'pass' : $npass? 'warn' : 'fail';
    } else {
        $rtext  = $errstr;
        $rclass = 'fail'
    }
    start 'td', class => $rclass;
    start 'a', href => "report.cgi?slot=$slot&amp;time=$date";
    print $rtext;
    end 'a';
    end 'td';
    end 'tr';
}
end 'table';
end 'body';
end 'html';
