# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008 - 2014 by Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.

"""
Import Music XML dialog.
Uses musicxml2ly to create ly file from xml.
In the dialog the options of musicxml2ly can be set.
"""


from PyQt6.QtCore import QSettings, QSize
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialogButtonBox, QLabel)

import app
import qutil
import job

from . import toly_dialog

# language names musicxml2ly allows
_langlist = [
    'nederlands',
    'catalan',
    'deutsch',
    'english',
    'espanol',
    'italiano',
    'norsk',
    'portugues',
    'suomi',
    'svenska',
    'vlaams',
]


class Dialog(toly_dialog.ToLyDialog):

    def __init__(self, parent=None):

        self.noartCheck = QCheckBox()
        self.norestCheck = QCheckBox()
        self.nolayoutCheck = QCheckBox()
        self.nobeamCheck = QCheckBox()
        self.useAbsCheck = QCheckBox()
        self.commMidiCheck = QCheckBox()

        self.langCombo = QComboBox()
        self.langLabel = QLabel()

        self.impChecks = [self.noartCheck,
                          self.norestCheck,
                          self.nolayoutCheck,
                          self.nobeamCheck,
                          self.useAbsCheck,
                          self.commMidiCheck]

        self.noartCheck.setObjectName("articulation-directions")
        self.norestCheck.setObjectName("rest-positions")
        self.nolayoutCheck.setObjectName("page-layout")
        self.nobeamCheck.setObjectName("import-beaming")
        self.useAbsCheck.setObjectName("absolute-mode")
        self.commMidiCheck.setObjectName("comment-out-midi")

        self.langCombo.addItem('')
        self.langCombo.addItems(_langlist)

        self.impExtra = [self.langLabel, self.langCombo]

        super().__init__(
            parent,
            imp_prgm="musicxml2ly",
            userg="musicxml_import")

        app.translateUI(self)
        qutil.saveDialogSize(self, "musicxml_import/dialog/size", QSize(480, 800))

        self.loadSettings()

    def translateUI(self):
        self.setWindowTitle(app.caption(_("Import Music XML")))
        self.noartCheck.setText(_("Import articulation directions"))
        self.norestCheck.setText(_("Import rest positions"))
        self.nolayoutCheck.setText(_("Import page layout"))
        self.nobeamCheck.setText(_("Import beaming"))
        self.useAbsCheck.setText(_("Pitches in absolute mode"))
        self.commMidiCheck.setText(_("Comment out midi block"))

        self.langLabel.setText(_("Language for pitch names"))
        self.langCombo.setItemText(0, _("Default"))

        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(_("Run musicxml2ly"))

        super().translateUI()

    def configure_job(self):
        super().configure_job()
        j = self._job
        if self.useAbsCheck.isChecked():
            j.add_argument('-a')
        if not self.noartCheck.isChecked():
            j.add_argument('--nd')
        if not self.norestCheck.isChecked():
            j.add_argument('--nrp')
        if not self.nolayoutCheck.isChecked():
            j.add_argument('--npl')
        if not self.nobeamCheck.isChecked():
            j.add_argument('--no-beaming')
        if not self.commMidiCheck.isChecked():
            j.add_argument('-m')
        index = self.langCombo.currentIndex()
        if index > 0:
            j.add_argument('--language=' + _langlist[index - 1])

    def loadSettings(self):
        """Get users previous settings."""
        self.imp_default = [False, False, False, False, False, False]
        self.settings = QSettings()
        self.settings.beginGroup('musicxml_import')
        super().loadSettings()
        lang = self.settings.value("language", "default", str)
        try:
            index = _langlist.index(lang)
        except ValueError:
            index = -1
        self.langCombo.setCurrentIndex(index + 1)

    def saveSettings(self):
        """Save users last settings."""
        self.settings = QSettings()
        self.settings.beginGroup('musicxml_import')
        super().saveSettings()
        index = self.langCombo.currentIndex()
        self.settings.setValue('language', 'default' if index == 0 else _langlist[index-1])
