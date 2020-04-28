#!/usr/bin/env python
# vim: filetype=python noet sw=4 ts=4

try:
	import	bunch
except:
	import	btrfscleaner.bunch

import	argparse
import	datetime
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

	def	bytes2str( self, b ):
		return str( b.decode( "utf-8" ) ) if isinstance( b, bytes ) else b

	def	printLn( self, s = '\n' ):
		if isinstance( s, list ):
			for part in s:
				self.printLn( part )
		else:
			for line in s.splitlines():
				print(
					self.bytes2str( line ),
					file = self.out if self.out else sys.stdout
				)
		return

	def	indent( self, s ):
		return '    {0}'.format( self.bytes2str( s ) )

	def	log( self, s, priority = syslog.LOG_ERR ):
		print(
			'{0}'.format( self.indent( s ) ),
			file = self.out if self.out else sys.stderr
		)
		syslog.syslog( priority, s )
		return

	def	new_node( self, where = None, dev = None ):
		return bunch.Bunch( where = where, dev = dev )

	def	select( self ):
		#
		# Make a local copy of the active mount table, then reduce it to
		# a dict of BTRFS mountpoint names.
		#
		with open( '/proc/mounts' ) as f:
			mounts = map(
				str.split,
				f.readlines(),
			)
		new_mounts  = [
			m[1] for m in mounts if m[2] == 'btrfs'
		]
		# print 'new_mounts={0}'.format( new_mounts )
		return new_mounts

	def	__init__(
		self,
		out = sys.stdout
	):
		# Get logging setup early
		syslog.openlog(
			'scrub-btrfs',
			syslog.LOG_PID,
			syslog.LOG_DAEMON,
		)
		self.out         = out
		# Record simple options
		self.opts        = bunch.Bunch()
		self.opts.dont   = False
		self.opts.filled = "1 2 3 5 7 10 15 20 30 40 50 60 70 80 90 100"
		return

	def	run( self, cmd, prolog = None ):
		cli = '{0} {1}'.format(
			'$' if os.getuid() else '#',
			' '.join( cmd )
		)
		err    = None
		if not prolog:
			prolog = list()
		elif type(prolog) != list:
			prolog = [ prolog ]
		output = prolog
		if self.opts.dont:
			output.append( cli )
		else:
			if self.opts.verbose:
				output.append( cli )
			try:
				s = subprocess.check_output(
					cmd,
					stderr = subprocess.STDOUT,
				)
				output.append( s )
			except subprocess.CalledProcessError as e:
				err = [ self.bytes2str( e.output ) ] +  [
					'Subprocess exit code {0}'.format( e.returncode ),
				]
			except Exception as e:
				print( '*** EXCEPTION {0}'.format( e ), file = sys.stderr )
				raise e
		return output, err

	def	_show( self, stuff, leadin = '' ):
		fmt = '{0:<2} {1}'
		for part in stuff:
			for line in part.splitlines():
				self.printLn(
					self.indent(
						fmt.format(
							leadin,
							self.bytes2str( line ),
						)
					)
				)
				pass
			pass
		return

	def	show( self, output = None, err = None ):
		if output:
			self._show( output )
		if err:
			self._show( err, leadin = '**' )
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
			output, err = self.run(
				cmd,
				prolog = 'Balancing {0}% usage'.format( fill ),
			)
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

	def	do_df( self, mp ):
		# Defrag
		cmd = [
			'/sbin/btrfs',
			'filesystem',
			'df',
			'--iec',
			mp
		]
		output, err = self.run( cmd )
		self.show( output, err )
		return

	def	do_du( self, mp = None ):
		if not mp:
			mp = self.opts.filesystems
		cmd = [
			'/sbin/btrfs',
			'filesystem',
			'du',
			'-s',
			'--iec',
		] + sorted( mp )
		output, err = self.run( cmd )
		self.show( output, err )
		return

	def	section( self, title, banner = None, step = True ):
		if step:
			self.step += 1
			leadin = '{0}. '.format( self.step )
		else:
			leadin = ''
			self.step = 0
		self.printLn()
		self.printLn(
			'{0}{1}'.format( leadin, title )
		)
		if banner:
			self.printLn(
				'{0}{1}'.format( '', banner * len( title ) )
			)
		self.printLn()
		return

	def	main( self ):
		prog = os.path.splitext(
			os.path.basename( sys.argv[0] )
		)[0]
		if prog == '__init__':
			prog = 'btrfs-cleaner-bis'
		p = argparse.ArgumentParser(
			prog        = prog,
			description = '''\
				Scrub btrfs filesystems in background
			''',
			formatter_class = argparse.ArgumentDefaultsHelpFormatter,
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
			print(
				'Not running as root; expect troubles.'
			)
		#
		ofile = self.opts.ofile
		self.out = open( ofile, 'wt' ) if ofile else sys.stdout
		#
		active_mounts = self.select()
		if len( self.opts.filesystems ) == 0:
			self.opts.filesystems = sorted( active_mounts )
		#
		if not any((
			self.opts.balance,
			self.opts.defrag,
			self.opts.scrub,
		)):
			self.opts.balance = True
			self.opts.defrag  = True
			self.opts.scrub   = True
		# For balancing, convert the space-delimited list of
		# usage thresholds into a list of numbers.
		if self.opts.balance:
			try:
				a = [
					int(x) for x in self.opts.filled.split()
				]
				self.opts.filled = a
			except:
				print(
					'Balance points must be numeric: {0}'.format(
						self.opts.filled,
					),
					file = sys.stderr
				)
				exit( 1 )
		#
		# Here we go
		#
		title = 'BTRFS Cleaning'
		self.printLn( title )
		self.printLn( '=' * len( title ) )
		self.printLn()
		# Make an establishing shot
		self.section( 'Filesystems Under Scrutiny', step = False )
		self.do_du()
		#
		uuids_already_processed = dict()
		for mp in sorted( self.opts.filesystems ):
			time_started = datetime.datetime.now()
			if mp not in active_mounts:
				print(
					'Not a mount point: {0}'.format(
						mp
					),
					file = sys.stderr
				)
				continue
			self.section(
				'Mountpoint "{0}"'.format( mp ),
				banner = '-',
				step = False,
			)
			# Make sure we can belive the filesystem metadata
			if self.opts.scrub:
				self.section( 'Scrubbing' )
				self.do_scrub( mp )
			# Be awesome
			self.section( 'Filesystem Topology' )
			self.do_df( mp )
			# Repack the filesystem to maximize free space
			if self.opts.balance:
				self.section( 'Balancing' )
				self.do_balance( mp )
			# Consolidate file disk usage
			if self.opts.defrag:
				self.section( 'Defragmenting (expect errors)' )
				self.do_defrag( mp )
			#
			self.section( 'Done' )
			time_ended = datetime.datetime.now()
			time_span  = time_ended - time_started
			fmt        = '{0:<8} {1:>27}'
			output     = [
				fmt.format( 'Ended',    str( time_ended )	),
				fmt.format( 'Started',  str( time_started )	),
				fmt.format( 'Duration', str( time_span )	),
			]
			self.show(
				output = output,
			)
		return 0

if __name__ == '__main__':
	exit( BtrfsCleaner().main() )
