"""Executed on launch maya."""

from maya import cmds

from maya_psyhive import startup

cmds.evalDeferred(startup.user_setup)
