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
            href => '/fate.css';
print "<title>FATE: $slot</title>\n";
end 'head';

start 'body';
h1 "Report history for $slot";

start 'table', id => 'history', class => 'replist';
start 'thead';
trowh 'Time', 'Arch', 'OS', 'Compiler', 'Rev', 'Result';
end 'thead';
start 'tbody';
for my $date (sort { $b cmp $a } @reps) {
    my $rep = load_summary $slot, $date or next;
    my $ntest = $$rep{ntests};
    my $npass = $$rep{npass};
    my $time = parse_date $$rep{date};
    my $age  = time - $time;
    my $rtext;
    my $rclass;

    start 'tr', class => 'alt hilight';
    td agestr $age, $time;
    td $$rep{subarch} || $$rep{arch};
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
        $rclass = 'fail'
    }
    start 'td', class => $rclass;
    anchor $rtext, href => href slot => $$rep{slot}, time => $$rep{date};
    end 'td';
    end 'tr';
    print "\n";
}
end 'tbody';
end 'table';
end 'body';
end 'html';
