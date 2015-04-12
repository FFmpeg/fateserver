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
                  start end tag h1 span trow trowa trowh th td anchor
                  head1 head2 head3 footer
                  fail $fatedir $recent_age $ancient_age $hidden_age href
                  $gitweb/;
}

our $fatedir = "/var/www/fateweb";
our $recent_age  = 3600;
our $ancient_age = 3 * 86400;
our $hidden_age  = 30 * 86400;
our $pretty_links = 0;
our $gitweb = "http://git.videolan.org/?p=ffmpeg.git";

#require "$ENV{FATEWEB_CONFIG}";

# report utils

sub split_header {
    my @hdr = split /:/, $_[0];
    $hdr[0] eq 'fate' or return undef;
    my $parsed = {
        version => $hdr[1],
        date    => $hdr[2],
        slot    => $hdr[3],
        rev     => $hdr[4],
        status  => $hdr[5],
        errstr  => $hdr[6],
        comment => $hdr[7],
    };
    if ($hdr[1] eq '1') {
      $parsed->{'comment'} = $hdr[8];
      $parsed->{'branch'}  = $hdr[7];
    }
    return $parsed;
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
        nfail  => int $st[1] - int $st[2],
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
    my $ntests = 0;
    my $npass = 0;
    while (<R>) {
        my $rec = split_rec $_;
        $$rec{status} == 0 and $npass++;
        $ntests++;
    }
    close R;
    return { %$hdr, %$conf, ntests => $ntests, npass => $npass,
             nfail => $ntests - $npass };
}

sub load_report {
    my ($slot, $date) = @_;
    my $report = "$fatedir/$slot/$date/report.xz";
    my @recs;

    return if not -f $report;

    open R, '-|', "unxz -c $report" or return;

    my $hdr  = split_header scalar <R> or return;
    my $conf = split_config scalar <R> or return;
    $$hdr{version} eq '0' or $$hdr{version} eq '1' or return undef;

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

sub head1 {
    print <<EOF;
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
EOF
}

sub head2 {
    # Copied from ffmpeg-web
    print <<EOF;
    <link rel="stylesheet" href="https://ffmpeg.org/css/font-awesome.min.css" />
    <link rel="stylesheet" href="https://ffmpeg.org/css/bootstrap.min.css" />
    <link rel="stylesheet" href="https://ffmpeg.org/css/simple-sidebar.css" />
    <link rel="stylesheet" href="https://ffmpeg.org/css/style.min.css" />
    <link rel="stylesheet" href="/fate.css" />
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <!--[if lt IE 9]>
      <script src="https://ffmpeg.org/js/html5shiv.min.js"></script>
      <script src="https://ffmpeg.org/js/respond.min.js"></script>
    <![endif]-->

    <link rel="shortcut icon" href="https://ffmpeg.org/favicon.ico" />
  </head>
  <body>

    <div id="wrapper">

      <nav id="sidebar-wrapper">
        <ul class="sidebar-nav">
          <li class="sidebar-brand"><a href=".">
              <img src="https://ffmpeg.org/img/ffmpeg3d_white_20.png" alt="FFmpeg" />
              FFmpeg</a>
          </li>
          <li><a href="https://ffmpeg.org/about.html">About</a></li>
          <li><a href="https://ffmpeg.org/index.html#news">News</a></li>
          <li><a href="https://ffmpeg.org/download.html">Download</a></li>
          <li><a href="https://ffmpeg.org/documentation.html">Documentation</a></li>
          <li><a href="https://ffmpeg.org/contact.html#MailingLists">Community</a>
            <ul>
              <li><a href="https://ffmpeg.org/contact.html#MailingLists">Mailing Lists</a></li>
              <li><a href="https://ffmpeg.org/contact.html#IRCChannels">IRC</a></li>
              <li><a href="https://ffmpeg.org/contact.html#Forums">Forums</a></li>
              <li><a href="https://ffmpeg.org/bugreports.html">Bug Reports</a></li>
              <li><a href="http://trac.ffmpeg.org">Wiki</a></li>
            </ul>
          </li>
          <li><a href="#">Developers</a>
            <ul>
              <li><a href="https://ffmpeg.org/download.html#get-sources">Source Code</a>
              <li><a href="/">FATE</a></li>
              <li><a href="http://coverage.ffmpeg.org">Code Coverage</a></li>
            </ul>
          </li>
          <li><a href="#">More</a>
            <ul>
              <li><a href="https://ffmpeg.org/donations.html">
                  Donate<span style="color: #e55; font-size: 0.8em; margin-left: -10px"><i class="fa fa-heart"></i></span></a></li>
              <li><a href="https://ffmpeg.org/consulting.html">Hire Developers</a></li>
              <li><a href="https://ffmpeg.org/contact.html">Contact</a></li>
              <li><a href="https://ffmpeg.org/security.html">Security</a></li>
              <li><a href="https://ffmpeg.org/legal.html">Legal</a></li>
            </ul>
          </li>
        </ul>
      </nav>

      <div id="page-content-wrapper">
        <header class="content-header">
          <h1>
            <a id="menu-toggle" href="#" class="btn btn-success"><i class="fa fa-reorder"></i></a>
EOF
}

sub head3 {
    print <<EOF;
          </h1>
        </header>
      <div class="page-content inset">
EOF
}

sub footer {
    print <<EOF
        </div> <!-- page-content-inset -->
      </div> <!-- page-content-wrapper -->
    </div> <!-- wrapper -->

    <script src="https://ffmpeg.org/js/jquery.min.js"></script>
    <script src="https://ffmpeg.org/js/bootstrap.min.js"></script>

    <!-- Custom JavaScript for the Menu Toggle -->
    <script>
      \$("#menu-toggle").click(function(e) {
          e.preventDefault();
          \$("#wrapper").toggleClass("active");
      });
    </script>

  </body>
</html>

EOF
}

sub fail {
    my ($msg) = @_;
    print "Content-type: text/html\r\n\r\n";
    print "<!DOCTYPE html>\n";
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
