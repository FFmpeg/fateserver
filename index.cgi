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
trowh 'Time', 'Arch', 'OS', 'Compiler', 'Rev', 'Status', 'Tests';
for my $slot (@slots) {
    open R, "$fatedir/$slot/latest/report";
    my @header = split /:/, scalar <R>;
    my @config = split /:/, scalar <R>;
    my ($date, $slot, $rev, $err, $errstr) = @header[2..6];
    my ($arch, $subarch, $cpu, $os, $cc) = @config[1..5];
    my $ntest;
    my $npass;
    while (<R>) {
        my @rec = split /:/;
        $rec[1] == 0 and $npass++;
        $ntest++;
    }
    close R;
    start 'tr';
    start 'td'; start 'a', href => "history.cgi?slot=$slot";
    print $date;
    end 'td';
    td $subarch;
    td $os;
    td $cc;
    td $rev;
    td $errstr, class => $err? 'fail' : 'pass';
    start 'td', class => $npass==$ntest? 'pass' : $npass? 'warn' : 'fail';
    start 'a', href => "report.cgi?slot=$slot&time=$date";
    print "$npass / $ntest";
    end 'a';
    end 'td';
    end 'tr';
}
end 'table';
end 'body';
end 'html';
