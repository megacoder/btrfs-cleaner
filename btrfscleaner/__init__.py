#!/usr/bin/python
# vim: filetype=python noet sw=4 ts=4

import	argparse
import	bunch
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

	def	fmt_code( self, s ):
		return '    {0}'.format( s )

	def	log( self, s, pri = syslog.LOG_ERR ):
		if self.out:
			print >>self.out, self.fmt_code( s )
		syslog.syslog( pri, s )
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
		mounts[:] = [
			m[1] for m in mounts if m[2] == 'btrfs'
		]
		# print 'mounts={0}'.format( mounts )
		return mounts

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
			except subprocess.CalledProcessError, e:
				err = [ e.output ] +  [
					'Exit code {0}'.format( e.returncode ),
				]
			except Exception, e:
				print '*** EXCEPTION {0}'.format( e )
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
		print
		print '{0}{1}'.format( leadin, title )
		if banner:
			print '{0}{1}'.format(
				' ' * len( leadin ),
				banner * len( title ),
			)
		print
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
			print >>sys.stderr, 'Not running as root; expect troubles.'
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
				print >>sys.stderr, 'Balance points must be numeric: {0}'.format(
						self.opts.filled,
					)
				exit( 1 )
		#
		title = 'BTRFS Cleaning'
		print title
		print '=' * len( title )
		self.section( 'Filesystems Under Scrutiny', step = False )
		self.do_du()
		uuids_already_processed = dict()
		for mp in sorted( self.opts.filesystems ):
			time_started = datetime.datetime.now()
			if mp not in active_mounts:
				print >>sys.stderr, 'Not a mount point: {0}'.format(
					mp
				)
				continue
			print
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
			time_span = time_ended - time_started
			fmt = '{0:<8} {1}'
			output = [
				fmt.format( 'Ended', time_ended ),
				fmt.format( 'Started', time_started ),
				fmt.format( 'Duration', time_span ),
			]
			self.show(
				output = output,
			)
		return 0

if __name__ == '__main__':
	exit( BtrfsCleaner().main() )
