# btrfs-cleaner
Do periodic maintenance on a BTRFS filesystem.  Yes, I'd call running this everynight "periodic."

##

    usage: btrfs-cleaner [-h] [-F FILLED] [-b] [-d] [-n] [-o OFILE] [-s] [-v]
                         [--version]
                         [mountpoint [mountpoint ...]]

    Scrub btrfs filesystems in background

    positional arguments:
      mountpoint            filesystems to scrub (default: [])

    optional arguments:
      -h, --help            show this help message and exit
      -F FILLED, --filled FILLED
                            list of balance points (default: 1 2 3 5 7 10 15 20 30
                            40 50 60 70 80 90 100)
      -b, --balance         balance filesystem (default: False)
      -d, --defrag          defragment files (default: False)
      -n, --dont            print what would be done (default: False)
      -o OFILE, --out OFILE
                            output here if not stdout (default: None)
      -s, --scrub           recalculate checksum of chunks (default: False)
      -v, --verbose         show command being run (default: False)
      --version             btrfs-cleaner v0.0.7

    If no action (defrag, balance, or scrub) is specified then all three actions
    will be performed.
