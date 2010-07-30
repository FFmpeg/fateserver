#! /usr/bin/perl

use strict;
use warnings;

use FATE;

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

start 'table', id => 'index', class => 'replist';
trowh 'Time', 'Arch', 'OS', 'Compiler', 'Rev', 'Result';
for my $slot (sort @slots) {
    my $rep = load_summary $slot, 'latest' or next;
    my $ntest = $$rep{ntests};
    my $npass = $$rep{npass};
    my $time = parse_date $$rep{date};
    my $age  = time - $time;
    my $agestr = agestr $age, $time;
    my $ageclass;
    my $rtext;
    my $rclass;

    if ($age < $recent_age) {
        $ageclass = 'recent';
    } elsif ($age > $ancient_age) {
        $ageclass = 'ancient';
    }

    start 'tr', class => $ageclass;
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
    end 'tr';
    print "\n";
}
end 'table';
end 'body';
end 'html';
