#! /usr/bin/perl

use strict;
use warnings;

use CGI qw/param/;
use FATE;

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
    my $hdr  = split_header scalar <R>;
    my $conf = split_config scalar <R>;
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

    my $time = parse_date $$hdr{date};
    my $age  = time - $time;

    start 'tr';
    td agestr $age, $time;
    td $$conf{subarch} || $$conf{arch};
    td $$conf{os};
    td $$conf{cc};
    td $$hdr{rev};
    if ($npass) {
        $rtext  = "$npass / $ntest";
        $rclass = $npass==$ntest? 'pass' : $npass? 'warn' : 'fail';
    } else {
        $rtext  = $$hdr{errstr};
        $rclass = 'fail'
    }
    start 'td', class => $rclass;
    anchor $rtext, href => "report.cgi?slot=$$hdr{slot}&amp;time=$$hdr{date}";
    end 'td';
    end 'tr';
    print "\n";
}
end 'table';
end 'body';
end 'html';
