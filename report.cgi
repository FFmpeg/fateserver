#! /usr/bin/perl

use strict;
use warnings;

use CGI qw/param/;
use HTML::Entities;
use MIME::Base64;
use FATE;

our $fatedir;
require "$ENV{FATEWEB_CONFIG}";

my $req_slot = param 'slot';
my $req_time = param 'time';

my $repdir = "$fatedir/$req_slot/$req_time";
my $report = "$repdir/report";

open R, $report or fail 'Requsted report not found';

my @header = split /:/, scalar <R>;
$header[0] eq 'fate' or die "Bad magic";
$header[1] eq '0'    or die "Bad report version";
my ($date, $slot, $rev, $err, $errstr) = @header[2..6];

my @config = split /:/, scalar <R>;
my ($arch, $subarch, $cpu, $os, $cc, $config) = @config[1..6];
if ($config[0] ne 'config') {
    print "Error in report: exptected 'config', found '$config[0]'\n";
    exit 1;
}

my @recs;
my %pass;
my %fail;

while (<R>) {
    my @rec = split /:/;
    ${$rec[1]? \%fail: \%pass}{$rec[0]} = \@rec;
}

close R;

my $npass = keys %pass;
my $nfail = keys %fail;
my $ntest = $npass + $nfail;

# main text

print "Content-type: text/html\r\n\r\n";

doctype;
start 'html', xmlns => "http://www.w3.org/1999/xhtml";
start 'head';
tag 'meta', 'http-equiv' => "Content-Type",
            'content'    => "text/html; charset=utf-8";
tag 'link', rel  => 'stylesheet',
            type => 'text/css',
            href => 'fate.css';
print "<title>FATE: $slot $rev</title>\n";
end 'head';

start 'body';
h1 "$slot $rev", id => 'title';

start 'table', id => 'config';
trow 'Architecture',  $arch;
trow 'Variant',       $subarch;
trow 'CPU',           $cpu;
trow 'OS',            $os;
trow 'Compiler',      $cc;
trow 'Configuration', $config;
trow 'Revision',      $rev;
trow 'Date',          $date;
trow 'Status',        $err? $errstr : "$npass / $ntest";
end;

start 'table', id => 'tests';
if ($nfail) {
    trowh 'Failed tests';
    for my $n (sort keys %fail) {
        my $rec = $fail{$n};
        my $diff = encode_entities decode_base64($$rec[2]), '<>&"';
        trowa { class => 'fail' }, $$rec[0];
        trowa { class => 'diff' }, $diff;
    }
} else {
    trowa { class => 'pass' }, 'All tests successful';
}
end 'table';

end 'body';
end 'html';
