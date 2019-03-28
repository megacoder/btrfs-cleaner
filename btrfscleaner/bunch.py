#!/usr/bin/python
# vim: noet sw=4 ts=4

import	sys
import	os

class	Bunch( dict ):

	def	__init__( self, **kwds ):
		super( Bunch, self ).__init__( **kwds )
		self.__dict__.update( **kwds )
		return

	def	__getattr__( self, name ):
		return self.__dict__.get( name, None )

	def	__setattr__( self, name, value ):
		self.__dict__[name] = value

	def	__getitem__( self, key ):
		return self.__dict__.get( key, None )

	def	__setitem__( self, key, value ):
		self.__dict__[ key ] = value
		return

	def	__delattr__( self, name ):
		if name in self.__dict__:
			del self.__dict__[name]
		return

	def	__iter__( self ):
		return iter( self.__dict__ )

	def	__repr__( self ):
		parts = [
			"'{0}': '{1}'".format( l, self.__dict__[l] ) for l in self.__dict__ if l[0] != '_'
		]
		return '{{ {0} }}'.format(
			'; '.join( parts )
		)

if __name__ == '__main__':
	b = Bunch(
		first = 'Tommy',
		last = 'Reynolds'
	)
	print 'Name: {0}, {1}, Should be none={2}'.format(
		b.last,
		b.first,
		b.no_such_value
	)
	print 'b={0}'.format( b )
	print 'last={0}'.format( b.get( 'last','BOO!' ) )
	print 'missing={0}'.format( b.get( ' *missing* ','BOO!' ) )
	print 'iter={0}'.format(
		[ x for x in b ]
	)
	print 'iter:'
	for i,key in enumerate( b ):
		print 'key[{0}]={1}'.format( i+1, key )
	exit( 0 )
