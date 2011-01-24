#! /usr/bin/perl

use strict;
use warnings;

use CGI qw/param/;
use FATE;

my $req_slot = param 'slot';
my $req_time = param 'time';
my ($req_log, $req_diff) = param('log') =~ m!([^/]+)(?:/([^/]+))?!;

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
