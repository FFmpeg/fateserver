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
use FATE;
use Time::Zone;
use HTML::Entities;

my $slot = param 'slot';
my $slotdir = "$fatedir/$slot";

my $slot_escaped = encode_entities $slot;

opendir D, $slotdir or fail "Slot $slot_escaped not found";
my @reps = grep { /^[0-9]/ and -d "$slotdir/$_" } readdir D;
close D;

@reps or fail "No data in $fatedir";

print "Content-type: text/html\r\n\r\n";

head1;
print "<title>FATE: $slot</title>\n";
head2;
print "Report history for $slot";
head3;

start 'div', class => 'table-responsive';
start 'table', id => 'history', class => 'replist table';
start 'thead';
trowh 'Time', 'Rev', 'Arch', 'OS', 'Compiler', 'Warnings', 'Tests';
end 'thead';
start 'tbody';
for my $date ((sort { $b cmp $a } @reps)[0..49]) {
    my $rep = load_summary $slot, $date or next;
    my $ntest = $$rep{ntests};
    my $npass = $$rep{npass};
    my $time = parse_date $$rep{date};
    my $age  = time - tz_local_offset() - $time;
    my $rtext;
    my $rclass;

    start 'tr', class => 'alt hilight';
    td agestr $age, $time;
    if ($gitweb and $$rep{rev} =~ /(N-)?(.*)/) {
        start 'td';
        anchor $$rep{rev}, href => "$gitweb;a=commit;h=$2";
        end 'td';
    } else {
        td $$rep{rev};
    }
    td $$rep{subarch} || $$rep{arch};
    td $$rep{os};
    td $$rep{cc};
    td $$rep{nwarn};
    if ($npass) {
        $rtext  = "$npass / $ntest";
        $rclass = $npass==$ntest? 'pass' : $npass? 'warn' : 'fail';
    } elsif (!$ntest and !$$rep{status}) {
        $rtext  = "build only";
        $rclass = $$rep{status}? 'fail' : 'pass';
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
end 'div';
footer;
