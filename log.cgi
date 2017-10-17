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

my $req_slot = param 'slot';
my $req_time = param 'time';
$req_slot =~ s/[^-._A-Za-z0-9 ]*//g;
$req_time =~ s/[^0-9]*//g;
my ($req_log, $req_diff) = param('log') =~ m!([^/]+)(?:/([^/]+))?!;
$req_log  =~ s/[^a-z]*//g;
$req_diff =~ s/[^0-9]*//g;

my $repdir = "$fatedir/$req_slot/$req_time";
my $log = "$repdir/$req_log.log.gz";

print "Content-type: text/plain\r\n";

if (! -r $log) {
    print "Status: 404 Not Found\r\n\r\n";
    print "Invalid log '$req_log' requested\n";
    exit;
}

if ($req_diff) {
    my $dlog = "$fatedir/$req_slot/$req_diff/$req_log.log.gz";
    print "\r\n";
    exec 'zdiff', '-u', $dlog, $log;
}

my $cat = 'zcat';

if ($ENV{HTTP_ACCEPT_ENCODING} =~ /gzip/) {
    print "Content-Encoding: gzip\r\n";
    $cat = 'cat';
}

print "\r\n";
exec $cat, $log;
