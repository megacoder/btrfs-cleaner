#!/usr/bin/python
# vim: filetype=python noet sw=4 ts=4

import	argparse
import	bunch
import	os
import	shlex
import	subprocess
import	sys
import	syslog

try:
	from version import Version
except:
	Version = 'W.T.F.'

class	BtrfsCleaner( object ):

	def	log( self, s, priority = syslog.LOG_ERR ):
		syslog.syslog( priority, s )
		return

	def	__init__(
		self
	):
		# Get logging setup early
		syslog.openlog(
			'scrub-btrfs',
			syslog.LOG_PID,
			syslog.LOG_DAEMON,
		)
		# Record simple options
		self.opts      = bunch.Bunch()
		self.opts.dont = False
		# Import /etc/fstab entries of interest
		self.btrfs     = dict()
		with open( '/etc/fstab' ) as f:
			for line in f:
				fields = shlex.split(
					line,
					comments = True,
					posix    = True
				)
				if len(fields) >= 4 and fields[2] == 'btrfs':
					self.btrfs[ fields[ 1 ] ] = fields
		return

	def	filesystem( self ):
		for i, key in enumerate( self.btrfs ):
			yield i, self.btrfs[key]
		return

	def	run( self, cmd ):
		cli = '{0} {1}'.format(
			'$' if os.getuid() else '#',
			' '.join( cmd )
		)
		err = None
		if self.opts.dont:
			output = cli
		else:
			if self.opts.verbose:
				print cli
			try:
				output = subprocess.check_output( cmd )
			except subprocess.CalledProcessError, e:
				output = e.output
				err = [
					cli,
					'Exit code {0}'.format( e.returncode ),
				]
			except Exception, e:
				print '*** {0}:{1} ***'.format( e.returncode, e.output )
				raise e
		return [ output ], err

	def	show( self, output = None, err = None ):
		if output:
			for part in output:
				for line in part.splitlines():
					print '  {0}'.format( line )
		if err:
			for part in err:
				for line in part.splitlines():
					print '* {0}'.format( line )
		return

	def	report( self ):
		pass

	def	do_scrub( self, fs ):
		# Scrub it
		cmd = [
			'/sbin/btrfs',
			'scrub',
			'start',
			'-B',
			'-d',
			'-f',
			fs
		]
		output, err = self.run( cmd )
		self.show( output, err )
		return

	def	do_balance( self, fs ):
		# Balance it
		cmd = [
			'/sbin/btrfs',
			'balance',
			'start',
			'-dusage=75',
			'-dlimit=8',
			'-musage=80',
			'-mlimit=32',
			fs
		]
		output, err = self.run( cmd )
		self.show( output, err )
		return

	def	do_defragment( self, fs ):
		# Defrag
		cmd = [
			'/sbin/btrfs',
			'filesystem',
			'defragment',
			'-f',
			'-r',
			mountpoint
		]
		output, err = self.run( cmd )
		self.show( output, err )
		return

	def	main( self ):
		prog = os.path.splitext(
			os.path.basename( sys.argv[0] )
		)[0]
		p = argparse.ArgumentParser(
			prog        = prog,
			description = 'Scrub btrfs filesystems in background'
		)
		p.add_argument(
			'-b',
			'--balance',
			dest   = 'balance',
			action = 'store_true',
			help   = 'balance filesystem'
		)
		p.add_argument(
			'-d',
			'--defrag',
			dest   = 'defrag',
			action = 'store_true',
			help   = 'defragment files',
		)
		p.add_argument(
			'-n',
			'--dont',
			dest    = 'dont',
			default = False,
			action  = 'store_true',
			help    = 'print what would be done'
		)
		p.add_argument(
			'-s',
			'--scrub',
			dest   = 'scrub',
			action = 'store_true',
			help   = 'recalculate checksum of chunks',
		)
		p.add_argument(
			'-v',
			'--verbose',
			dest   = 'verbose',
			action = 'store_true',
			help   = 'show command being run',
		)
		p.add_argument(
			'--version',
			action  = 'version',
			version = Version,
			help    = '{0} v{1}'.format( prog, Version )
		)
		p.add_argument(
			'filesystems',
			metavar = 'mountpoint',
			nargs = '*',
			default = [],
			help = 'filesystems to scrub'
		)
		self.opts = p.parse_args()
		if len( self.opts.filesystems ) == 0:
			self.opts.filesystems = self.btrfs
		#
		if not any(
			self.opts.balance,
			self.opts.defrag,
			self.opts.scrub,
		):
			self.opts.balance = True
			self.opts.defrag  = True
			self.opts.scrub   = True
		#
		for mountpoint in sorted( self.opts.filesystems ):
			title = 'Mountpoint: {0}'.format( mountpoint )
			print
			print title
			print '-' * len( title )
			print
			if mountpoint not in self.btrfs:
				print >>sys.stderr, '{0} is not a BTRFS mount.'.format(
					mountpoint
				)
				continue
			if self.opts.scrub:
				self.do_scrub( mountpoint )
			if self.opts.balance:
				self.do_balance( mountpount )
			if self.opts.defrag:
				self.do_defrag( mountpoint )
		return 0

if __name__ == '__main__':
	exit( BtrfsCleaner().main() )
