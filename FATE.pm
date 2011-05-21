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

package FATE;

use strict;
use warnings;

use POSIX qw/asctime mktime/;

BEGIN {
    use Exporter;
    our ($VERSION, @ISA, @EXPORT);
    $VERSION = 0.1;
    @ISA     = qw/Exporter/;
    @EXPORT  = qw/split_header split_config split_rec parse_date agestr
                  split_stats load_summary load_report load_lastpass
                  doctype start end tag h1 span trow trowa trowh th td anchor
                  fail $fatedir $recent_age $ancient_age $hidden_age href
                  $gitweb/;
}

our $fatedir;
our $recent_age  = 3600;
our $ancient_age = 3 * 86400;
our $hidden_age  = 30 * 86400;
our $pretty_links = 0;
our $gitweb;

require "$ENV{FATEWEB_CONFIG}";

# report utils

sub split_header {
    my @hdr = split /:/, $_[0];
    $hdr[0] eq 'fate' or return undef;
    return {
        version => $hdr[1],
        date    => $hdr[2],
        slot    => $hdr[3],
        rev     => $hdr[4],
        status  => $hdr[5],
        errstr  => $hdr[6],
        comment => $hdr[7],
    };
}

sub split_config {
    my @conf = split /:/, $_[0];
    $conf[0] eq 'config' or return undef;
    return {
        arch    => $conf[1],
        subarch => $conf[2],
        cpu     => $conf[3],
        os      => $conf[4],
        cc      => $conf[5],
        config  => $conf[6],
    };
}

sub split_stats {
    my @st = split /:/, $_[0];
    $st[0] eq 'stats' or return undef;
    return {
        ntests => int $st[1],
        npass  => int $st[2],
        nwarn  =>     $st[3],
    };
}

sub split_rec {
    my @rec = split /:/, $_[0];
    return {
        name   => $rec[0],
        status => $rec[1],
        diff   => $rec[2],
        stderr => $rec[3],
    };
}

sub load_summary {
    my ($slot, $date) = @_;
    my $repdir = "$fatedir/$slot/$date";
    return if not -d $repdir;

    if (open S, "$repdir/summary") {
        my $hdr  = split_header scalar <S> or return;
        my $conf = split_config scalar <S> or return;
        my $st   = split_stats  scalar <S> or return;
        close S;
        return { %$hdr, %$conf, %$st };
    }

    return if not -f "$repdir/report.xz";
    open R, '-|', "unxz -c $repdir/report.xz" or return;
    my $hdr  = split_header scalar <R> or return;
    my $conf = split_config scalar <R> or return;
    my $ntest = 0;
    my $npass = 0;
    while (<R>) {
        my $rec = split_rec $_;
        $$rec{status} == 0 and $npass++;
        $ntest++;
    }
    close R;
    return { %$hdr, %$conf, ntests => $ntest, npass => $npass };
}

sub load_report {
    my ($slot, $date) = @_;
    my $report = "$fatedir/$slot/$date/report.xz";
    my @recs;

    return if not -f $report;

    open R, '-|', "unxz -c $report" or return;

    my $hdr  = split_header scalar <R> or return;
    my $conf = split_config scalar <R> or return;
    $$hdr{version} eq '0'              or return undef;

    while (<R>) {
        my $rec = split_rec $_;
        push @recs, $rec;
    }

    close R;

    return { header => $hdr, conf => $conf, recs => \@recs };
}

sub load_lastpass {
    my ($slot) = @_;
    my %lastpass;

    if (open P, "$fatedir/$slot/lastpass") {
        while (<P>) {
            my ($test, $pdate, $prev) = split /:/;
            $lastpass{$test} = { date => $pdate, rev => $prev };
        }
        close P;
    }

    return \%lastpass;
}

sub parse_date {
    $_[0] =~ /^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})$/ or return undef;
    mktime $6, $5, $4, $3, $2-1, $1-1900;
}

sub agestr {
    my ($age, $time) = @_;

    if ($age <= 0) {
        return 'Right now';
    } elsif ($age > 14 * 86400) {
        return POSIX::strftime "%F", gmtime $time;
    }

    my $agestr;

    if ($age < 60) {
        $agestr = 'second';
    } elsif ($age < 60 * 120) {
        $age /= 60;
        $agestr = 'minute';
    } elsif ($age < 48 * 3600) {
        $age /= 3600;
        $agestr = 'hour';
    } else {
        $age /= 86400;
        $agestr = 'day';
    }

    $agestr .= 's' if int $age > 1;
    return sprintf "%d $agestr ago", $age;
}

# HTML helpers

my %block_tags;
my @block_tags = ('html', 'head', 'style', 'body', 'table');
$block_tags{$_} = 1 for @block_tags;

my @tags;

sub doctype {
    print q{<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">}, "\n";
}

sub opentag {
    my ($tag, %attrs) = @_;
    print qq{<$tag};
    print qq{ $_="$attrs{$_}"} for grep defined $attrs{$_}, keys %attrs;
}

sub start {
    my ($tag, %attrs) = @_;
    opentag @_;
    print '>';
    print "\n" if defined $block_tags{$tag};
    push @tags, $tag;
}

sub end {
    my ($end) = @_;
    my $tag;
    do {
        $tag = pop @tags or last;
        print "</$tag>";
        print "\n" if defined $block_tags{$tag};
    } while (defined $end and $tag ne $end);
}

sub tag {
    opentag @_;
    print "/>\n";
}

sub h1 {
    my ($text, %attrs) = @_;
    start 'h1', %attrs;
    print $text;
    end;
    print "\n";
}

sub span {
    my ($text, %attrs) = @_;
    start 'span', %attrs;
    print $text;
    end;
}

sub trow {
    start 'tr';
    print "<td>$_</td>" for @_;
    end;
    print "\n";
}

sub trowh {
    start 'tr';
    print "<th>$_</th>" for @_;
    end;
    print "\n";
}

sub trowa {
    my $attrs = shift;
    start 'tr', %{$attrs};
    print "<td>$_</td>" for @_;
    end;
    print "\n";
}

sub th {
    my ($text, %attrs) = @_;
    start 'th', %attrs;
    print $text;
    end;
}

sub td {
    my ($text, %attrs) = @_;
    start 'td', %attrs;
    print $text;
    end;
}

sub anchor {
    my ($text, %attrs) = @_;
    start 'a', %attrs;
    print $text;
    end;
}

sub href {
    my (%href) = @_;
    if ($pretty_links) {
        my @parts = ('slot', 'time', 'log');
        return '/' . join '/', grep defined $_, @href{@parts};
    } else {
        my $cgi = defined $href{log}? 'log': defined $href{time}? 'report': 'history';
        return sprintf '/%s.cgi?%s', $cgi, join '&amp;', map "$_=$href{$_}", keys %href;
    }
}

sub fail {
    my ($msg) = @_;
    print "Content-type: text/html\r\n\r\n";
    doctype;
    start 'html', xmlns => "http://www.w3.org/1999/xhtml";
    start 'head';
    tag 'meta', 'http-equiv' => "Content-Type",
                'content'    => "text/html; charset=utf-8";
    print "<title>FATE error</title>\n";
    end 'head';

    start 'body';
    h1 "FATE error", id => 'title';
    print "$msg\n";
    end 'body';
    end 'html';
    exit 1;
}

1;
