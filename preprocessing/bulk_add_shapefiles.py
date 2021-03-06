# -*- coding: utf-8 -*-
"""
Created on Wed Mar 25 10:15:18 2020
@author: Daniel
"""
from qgis.core import QgsLayerTreeGroup, QgsVectorLayer, QgsProject, QgsTask, QgsApplication, QgsSymbol, QgsRendererRange, QgsStyle, QgsGraduatedSymbolRenderer
import os, glob, traceback, fnmatch, time, threading, qgis
import os, glob, traceback, fnmatch, time, threading, qgis
from datetime import datetime
from osgeo import ogr
from qgis.utils import iface
#add vectors

def findGroup(root:QgsLayerTreeGroup, name:str) -> QgsLayerTreeGroup:
	"""Recursively finds first group that matches name."""
	#Search immediate children
	for child in root.children():
		if isinstance(child, QgsLayerTreeGroup):
			if name == child.name():
				return child
	#Search subchildren
	for child in root.children():
		if isinstance(child, QgsLayerTreeGroup):
			result = findGroup(child, name)
			if result != None:
				return result
	#Found nothing
	return None

def findChildren(root:QgsLayerTreeGroup, matchString:str):
	"""Return a list of groups in the root that match a regex string argument."""
	result = []
	matchStringParts = matchString.split('/', 1)
	for child in root.children():
		if fnmatch.fnmatch(child.name(), matchStringParts[0]):
			if isinstance(child, QgsLayerTreeGroup):
				result.extend(findChildren(child, matchStringParts[1]))
			else:
				result.append(child)
	return result

def layerFromPath(lineFilePath:str, rootGroup:QgsLayerTreeGroup,  project:QgsLayerTreeGroup) -> None:
	lineFileBasename = os.path.splitext(os.path.basename(lineFilePath))[0]
	lineLayer = QgsVectorLayer(lineFilePath, lineFileBasename, 'ogr')
	
	# Get number of features (range of Sequence#, number of renderer color classes)
	driver = ogr.GetDriverByName('ESRI Shapefile')
	dataSource = driver.Open(lineFilePath, 0) # 0 means read-only. 1 means writeable.
	layer = dataSource.GetLayer()
	dataSource = None
	
	#Setup graduated color renderer based on year
	targetField = 'Year'
	renderer = QgsGraduatedSymbolRenderer('', [QgsRendererRange()])
	renderer.setClassAttribute(targetField)
	lineLayer.setRenderer(renderer)
	
	#Get viridis color ramp
	style = QgsStyle().defaultStyle()
	defaultColorRampNames = style.colorRampNames()
	viridisIndex = defaultColorRampNames.index('Viridis')
	viridisColorRamp = style.colorRamp(defaultColorRampNames[viridisIndex]) #Spectral color ramp
	
	#Dynamically recalculate number of classes and colors
	renderer.updateColorRamp(viridisColorRamp)
	yearsRange = list(range(1972, 2020))
	classCount = len(yearsRange)
	renderer.updateClasses(lineLayer, QgsGraduatedSymbolRenderer.EqualInterval, classCount)
	
	#Set graduated color renderer based on Sequence#
	for i in range(classCount): #[1972-2019], 2020 not included
		targetField = 'DateUnix'
		year = yearsRange[i]
		renderer.updateRangeLowerValue(i, year)
		renderer.updateRangeUpperValue(i, year)
		
	project.addMapLayer(lineLayer, False)
	rootGroup.insertLayer(0, lineLayer)

class TestTask( QgsTask ):
	def __init__(self, desc, sourcePath, destGroup):
		QgsTask.__init__(self, desc)
		self.sourcePath = sourcePath
		self.destGroup = destGroup
		
	def bulkAdd(self):
		project = QgsProject.instance()
		root = project.layerTreeRoot()
		rootGroup = findGroup(root, self.destGroup)
		
		# For each domain in CalvingFronts...
		shapefilesPathList = sorted(glob.glob(os.path.join(self.sourcePath, '*.shp')))
		numShapefiles = len(shapefilesPathList)
		for i in reversed(range(numShapefiles)):
			self.setProgress((i) / numShapefiles * 50)
			lineFilePath = shapefilesPathList[i]
			layerFromPath(lineFilePath, rootGroup, project)
			self.setProgress((i + 1) / numShapefiles * 50)
			
	def run(self):
		try:
			self.bulkAdd()
		except:
			traceback.print_exc()
		self.completed()

sourcePath = r'level-1_shapefiles-domain-termini'
destGroup = 'CalvingFronts'
task = TestTask('Adding Shapefiles...', sourcePath, destGroup) 
QgsApplication.taskManager().addTask(task)

print('If an error occured, check the source path & destination group:', sourcePath, destGroup)
