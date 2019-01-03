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

	def	fmt_code( self, s ):
		return '    {0}'.format( s )

	def	log( self, s, pri = syslog.LOG_ERR ):
		if self.out:
			print >>self.out, self.fmt_code( s )
		syslog.syslog( pri, s )
		return

	def	new_node( self, mp = None, uuid = None ):
		return bunch.Bunch( mp = mp, uuid = uuid )

	def	select( self ):
		#
		self.uuids = dict()
		rootdir = '/sys/fs/btrfs'
		for uuid in os.listdir( rootdir ):
			fs = os.path.join(
				rootdir,
				uuid,
				'label'
			)
			if os.path.exists( fs ):
				self.uuids[ uuid ] = list()
		# See which BTRFS (sub)volumes are mounted
		self.mounts = dict()
		with open( '/proc/mounts' ) as f:
			for line in f:
				tokens = line.split()
				mp = tokens[ 1 ]
				fs = tokens[ 2 ]
				if fs == 'btrfs':
					self.mounts[ mp ] = self.new_node( mp = mp )
		# See which /etc/fstab BTRFS partitions are mounted
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
					uuid = tokens[ 0 ]
					mp   = tokens[ 1 ]
					fs   = tokens[ 2 ]
					if uuid.startswith( 'UUID=' ):
						if mp in self.mounts:
							uuid = uuid[ 5: ]
							self.uuids[ uuid ].append( mp )
							self.mounts[ mp ].uuid = uuid
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
		self.out         = None
		# Record simple options
		self.opts        = bunch.Bunch()
		self.opts.dont   = False
		self.opts.filled = "1 2 3 5 7 10 15 20 30 40 50 60 70 80 90 100"
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
			output = [ cli ]
		else:
			output = []
			if self.opts.verbose:
				output += [ cli ]
			try:
				output += [
					subprocess.check_output(
						cmd,
						stderr = subprocess.STDOUT,
					)
				]
			except subprocess.CalledProcessError, e:
				err = [ e.output ] +  [
					'Exit code {0}'.format( e.returncode ),
				]
			except Exception, e:
				print '*** {0}:{1} ***'.format( e.returncode, e.output )
				raise e
		return output, err

	def	show( self, output = None, err = None ):
		fmt = '{0:<2} {1}'
		if output and len(output):
			for part in output:
				for line in part.splitlines():
					print self.fmt_code( fmt.format( '', line ) )
		if err and len(err):
			for part in err:
				for line in part.splitlines():
					print self.fmt_code( fmt.format( '**', line ) )
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
		for fill in self.opts.filled:
			cmd = [
				'/sbin/btrfs',
				'balance',
				'start',
				'-dusage={0}'.format( fill ),
#				'-dlimit=32',
				'-musage={0}'.format( fill ),
#				'-mlimit=32',
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
			'-F',
			'--filled',
			dest    ='filled',
			help    = 'list of balance points',
			default = self.opts.filled,
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
		self.select()
		if len( self.opts.filesystems ) == 0:
			self.opts.filesystems = [ self.uuids[u][0] for u in self.uuids ]
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
		if self.opts.balance:
			try:
				a = [
					int(x) for x in self.opts.filled.split()
				]
				self.opts.filled = a
			except:
				print >>sys.stderr, 'Balance points must be numeric: {0}'.format(
						self.opts.filled,
					)
				exit( 1 )
		#
		title = 'BTRFS Cleaning'
		print title
		print '=' * len( title )
		uuids_already_processed = dict()
		for mp in sorted( self.opts.filesystems ):
			if mp not in self.mounts:
				print >>sys.stderr, 'Not a mount point: {0}'.format(
					mp
				)
				continue
			uuid = self.mounts[ mp ].uuid
			if uuid in uuids_already_processed:
				print >>sys.stderr, 'Skipping {0}, already done {1}'.format(
					mp,
					uuid,
				)
				continue
			uuids_already_processed[ uuid ] = mp
			title = 'Mountpoint: {0}'.format( mp )
			print
			print
			print title
			print '-' * len( title )
			step = 0
			# Make sure we can belive the filesystem metadata
			if self.opts.scrub:
				step += 1
				print
				print '{0}. Scrubbing'.format( step )
				print
				self.do_scrub( mp )
			# Repack the filesystem to maximize free space
			if self.opts.balance:
				step += 1
				print
				print '{0}. Balancing'.format( step )
				print
				self.do_balance( mp )
			# Consolidate file disk usage
			if self.opts.defrag:
				step += 1
				print
				print '{0}. Defragmenting'.format( step )
				print
				self.do_defrag( mp )
		return 0

if __name__ == '__main__':
	exit( BtrfsCleaner().main() )
