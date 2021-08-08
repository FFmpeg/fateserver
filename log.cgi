#! /usr/bin/perl -T
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

use lib "/var/www/fateweb";

use FATE;

cgi_path_is_trustworthy;

my $req_slot = safeparam_slot;
my $req_time = safeparam_time;
my $req_log = safeparam_log;
my $req_diff;
$req_diff = $1 if $req_log =~ s/\/(.*)//;

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
    end_headers_and_compress;
    exec 'zdiff', '-u', $dlog, $log;
}

my $cat = 'zcat';

if (ready_for_gzip) {
    $cat = 'cat';
}

exec $cat, $log;
