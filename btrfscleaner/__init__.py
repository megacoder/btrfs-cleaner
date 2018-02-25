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

	def	log( self, s, pri = syslog.LOG_ERR ):
		if self.out:
			print >>self.out, s
		syslog.syslog( pri, s )
		return

	def	select( self ):
		# See which BTRFS (sub)volumes are mounted
		mp_to_uuid = dict()
		with open( '/proc/mounts' ) as f:
			for line in f:
				tokens = line.split()
				mp = tokens[ 1 ]
				fs = tokens[ 2 ]
				if fs == 'btrfs':
					mp_to_uuid[ mp ] = None
		# See which UUID mounts that in /etc/fstab
		with open( '/etc/fstab' ) as f:
			for line in f:
				tokens = [
					t for t in shlex.split(
						line,
						posix    = True,
						comments = True,
					)
				]
				if len( tokens ) >= 3:
					device = tokens[ 0 ]
					mp     = tokens[ 1 ]
					fs     = tokens[ 2 ]
					if mp in mp_to_uuid:
						if fs == 'btrfs' and device.startswith( 'UUID=' ):
							uuid = device[ 5: ]
							mp_to_uuid[ mp ] = uuid
		return mp_to_uuid

	def	__init__(
		self
	):
		# Get logging setup early
		syslog.openlog(
			'scrub-btrfs',
			syslog.LOG_PID,
			syslog.LOG_DAEMON,
		)
		self.out = None
		# Record simple options
		self.opts      = bunch.Bunch()
		self.opts.dont = False
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
			self.log( cli, syslog.LOG_NOTICE )
			output = None
		else:
			if self.opts.verbose:
				print cli
			try:
				output = [ subprocess.check_output( cmd ) ]
			except subprocess.CalledProcessError, e:
				output = [ e.output ]
				err = [
					cli,
					'Exit code {0}'.format( e.returncode ),
				]
			except Exception, e:
				print '*** {0}:{1} ***'.format( e.returncode, e.output )
				raise e
		return output, err

	def	show( self, output = None, err = None ):
		fmt = '    {0:<2} {1}'
		if output and len(output):
			for part in output:
				for line in part.splitlines():
					print fmt.format( '', line )
		if err and len(err):
			for part in err:
				for line in part.splitlines():
					print fmt.format( '*', line )
		return

	def	report( self ):
		pass

	def	do_scrub( self, mp ):
		# Scrub it
		cmd = [
			'/sbin/btrfs',
			'scrub',
			'start',
			'-B',
			'-d',
			'-f',
			mp
		]
		output, err = self.run( cmd )
		self.show( output, err )
		return

	def	do_balance( self, mp ):
		# Balance it
		cmd = [
			'/sbin/btrfs',
			'balance',
			'start',
			'-dusage=75',
			'-dlimit=32',
			'-musage=80',
			'-mlimit=32',
			mp
		]
		output, err = self.run( cmd )
		self.show( output, err )
		return

	def	do_defrag( self, mp ):
		# Defrag
		cmd = [
			'/sbin/btrfs',
			'filesystem',
			'defragment',
			'-f',
			'-r',
			mp
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
			description = '''\
				Scrub btrfs filesystems in background
			''',
			epilog = '''\
				If no action (defrag, balance, or scrub) is specified then
				all three actions will be performed.
			'''
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
			'-o',
			'--out',
			dest = 'ofile',
			help = 'output here if not stdout',
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
		if os.getuid() != 0:
			print >>sys.stderr, 'Not running as root; expect troubles.'
		#
		ofile = self.opts.ofile
		self.out = open( ofile, 'wt' ) if ofile else sys.stdout
		#
		mp_to_uuid = self.select()
		if len( self.opts.filesystems ) == 0:
			self.opts.filesystems = mp.to_uuid.keys()
		#
		if not any((
			self.opts.balance,
			self.opts.defrag,
			self.opts.scrub,
		)):
			self.opts.balance = True
			self.opts.defrag  = True
			self.opts.scrub   = True
		#
		title = 'BTRFS Cleaning'
		print title
		print '=' * len( title )
		uuid_already_done = dict()
		for mp in sorted( self.opts.filesystems ):
			uuid = mp_to_uuid[ mp ]
			if uuid in uuid_already_done:
				print >>sys.stderr, 'Skipping {0}, already done {1}'.format(
					mp,
					uuid,
				)
				continue
			uuid_already_done[ uuid ] = mp
			title = 'Mountpoint: {0}'.format( mp )
			print
			print
			print title
			print '-' * len( title )
			step = 0
			if self.opts.scrub:
				step += 1
				print
				print '{0}. Scrubbing'.format( step )
				print
				self.do_scrub( mp )
			if self.opts.balance:
				step += 1
				print
				print '{0}. Balancing'.format( step )
				print
				self.do_balance( mp )
			if self.opts.defrag:
				step += 1
				print
				print '{0}. Defragmenting'.format( step )
				print
				self.do_defrag( mp )
		return 0

if __name__ == '__main__':
	exit( BtrfsCleaner().main() )
