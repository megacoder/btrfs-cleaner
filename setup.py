#!/usr/bin/env python
# vim: nonu noet ai sm ts=4 sw=4

from setuptools import setup, find_packages

Name    = 'btrfscleaner'
Runtime	= 'btrfs-cleaner'
Version = '0.1.0'

with open( '{0}/version.py'.format( Name ), 'wt' ) as f:
    print( 'Version = "{0}"'.format( Version ), file = f )

setup(
    name				= Name,
    version				= Version,
    description			= 'BTRFFS periodic maintenance',
	long_description	= open( 'README.md' ).read(),
    url					= 'http://www.megacoder.com',
    author				= 'Tommy Reynolds',
    author_email		= 'oldest.software.guy@gmail.com',
    packages			= [ Name ],
    scripts				= [
        '{0}/scripts/{1}'.format(
			Name,
			Runtime
		),
    ]
)

