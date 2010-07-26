#! /usr/bin/perl

use strict;
use warnings;

use FATE;

our $fatedir;
require "$ENV{FATEWEB_CONFIG}";

opendir D, $fatedir or fail 'Server error: $fatedir not found';
my @slots = grep /^[^.]/, readdir D;
closedir D;

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
end 'head';

start 'body';
h1 'FATE';

start 'table', id => 'index';
trowh 'Time', 'Arch', 'OS', 'Compiler', 'Rev', 'Result';
for my $slot (sort @slots) {
    open R, "$fatedir/$slot/latest/report";
    my $hdr  = split_header scalar <R>;
    my $conf = split_config scalar <R>;
    my $ntest = 0;
    my $npass = 0;
    my $rtext;
    my $rclass;
    while (<R>) {
        my $rec = split_rec $_;
        $$rec{status} == 0 and $npass++;
        $ntest++;
    }
    close R;

    my $time = parse_date $$hdr{date};
    my $age  = time - $time;
    my $agestr = agestr $age, $time;
    my $ageclass;

    if ($age < 3600) {
        $ageclass = 'recent';
    } elsif ($age > 3 * 86400) {
        $ageclass = 'ancient';
    }

    start 'tr', class => $ageclass;
    start 'td';
    anchor $agestr, href => "history.cgi?slot=$$hdr{slot}";
    end 'td';
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
