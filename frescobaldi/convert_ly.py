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
Updates a document using convert-ly.
"""


import difflib
import textwrap
import os
import platform
import sys

from PyQt6.QtCore import QSettings, QSize
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QTabWidget, QTextBrowser, QVBoxLayout)

import app
import job
import util
import qutil
import icons
import widgets
import htmldiff
import cursordiff
import lilychooser
import documentinfo
import textformats


def convert(mainwindow):
    """Shows the dialog."""
    dlg = Dialog(mainwindow)
    dlg.addAction(mainwindow.actionCollection.help_whatsthis)
    dlg.setDocument(mainwindow.currentDocument())
    dlg.setModal(True)
    dlg.show()
    dlg.run()
    if dlg.exec():
        c = mainwindow.textCursor()
        c.select(QTextCursor.SelectionType.Document)
        text = dlg.convertedText()
        if dlg.copyCheck.isChecked():
            msgs = textwrap.fill(dlg.messages.toPlainText())
            text += '\n\n%{\n' + msgs + '\n%}\n'
        cursordiff.insert_text(c, text)
    dlg.deleteLater()


class Dialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._info = None
        self._text = ''
        self._convertedtext = ''
        self._encoding = None
        self.mainwindow = parent

        self.fromVersionLabel = QLabel()
        self.fromVersion = QLineEdit()
        self.reason = QLabel()
        self.toVersionLabel = QLabel()
        self.toVersion = QLineEdit()
        self.lilyChooser = lilychooser.LilyChooser(toolcommand='convert-ly')
        self.messages = QTextBrowser()
        self.diff = QTextBrowser(lineWrapMode=QTextBrowser.LineWrapMode.NoWrap)
        self.uni_diff = QTextBrowser(lineWrapMode=QTextBrowser.LineWrapMode.NoWrap)
        self.copyCheck = QCheckBox(checked=
            QSettings().value('convert_ly/copy_messages', True, bool))
        self.tabw = QTabWidget()

        self.tabw.addTab(self.messages, '')
        self.tabw.addTab(self.diff, '')
        self.tabw.addTab(self.uni_diff, '')

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Reset | QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).clicked    .connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(self.run)
        self.buttons.button(QDialogButtonBox.StandardButton.Save).clicked.connect(self.saveFile)

        layout = QVBoxLayout()
        self.setLayout(layout)

        grid = QGridLayout()
        grid.addWidget(self.fromVersionLabel, 0, 0)
        grid.addWidget(self.fromVersion, 0, 1)
        grid.addWidget(self.reason, 0, 2, 1, 3)
        grid.addWidget(self.toVersionLabel, 1, 0)
        grid.addWidget(self.toVersion, 1, 1)
        grid.addWidget(self.lilyChooser, 1, 3, 1, 2)

        layout.addLayout(grid)
        layout.addWidget(self.tabw)
        layout.addWidget(self.copyCheck)
        layout.addWidget(widgets.Separator())
        layout.addWidget(self.buttons)

        app.translateUI(self)
        qutil.saveDialogSize(self, 'convert_ly/dialog/size', QSize(600, 300))
        app.settingsChanged.connect(self.readSettings)
        self.readSettings()
        self.finished.connect(self.saveCopyCheckSetting)
        self.lilyChooser.currentIndexChanged.connect(self.slotLilyPondVersionChanged)
        self.slotLilyPondVersionChanged()

    def translateUI(self):
        self.fromVersionLabel.setText(_("From version:"))
        self.toVersionLabel.setText(_("To version:"))
        self.copyCheck.setText(_("Save convert-ly messages in document"))
        self.copyCheck.setToolTip(_(
            "If checked, the messages of convert-ly are appended as a "
            "comment to the end of the document."))
        self.tabw.setTabText(0, _("&Messages"))
        self.tabw.setTabText(1, _("&Changes"))
        self.tabw.setTabText(2, _("&Diff"))
        self.buttons.button(QDialogButtonBox.StandardButton.Reset).setText(_("Run Again"))
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setText(_("Save as file"))
        self.setCaption()

    def saveCopyCheckSetting(self):
        QSettings().setValue('convert_ly/copy_messages', self.copyCheck.isChecked())

    def readSettings(self):
        font = textformats.formatData('editor').font
        self.diff.setFont(font)
        diffFont = QFont("Monospace")
        diffFont.setStyleHint(QFont.StyleHint.TypeWriter)
        self.uni_diff.setFont(diffFont)

    def slotLilyPondVersionChanged(self):
        self.setLilyPondInfo(self.lilyChooser.lilyPondInfo())

    def setCaption(self):
        version = self._info and self._info.versionString() or _("<unknown>")
        title = _("Convert-ly from LilyPond {version}").format(version=version)
        self.setWindowTitle(app.caption(title))

    def setLilyPondInfo(self, info):
        if not info:
            return
        self._info = info
        self.setCaption()
        self.toVersion.setText(info.versionString())
        self.setConvertedText()
        self.setDiffText()
        self.messages.clear()

    def setConvertedText(self, text=''):
        self._convertedtext = text
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(text))
        if text:
            self.diff.setHtml(htmldiff.htmldiff(
                self._text, text,
                _("Current Document"), _("Converted Document"),
                wrapcolumn=100))
        else:
            self.diff.clear()

    def setDiffText(self, text=''):
        if text:
            from_filename = "current"   # TODO: maybe use real filename here
            to_filename = "converted"   # but difflib can choke on non-ascii characters,
                                        # see https://github.com/frescobaldi/frescobaldi/issues/674
            difflist = list(difflib.unified_diff(
                    self._text.split('\n'), text.split('\n'),
                    from_filename, to_filename))
            diffHLstr = self.diffHighl(difflist)
            self.uni_diff.setHtml(diffHLstr)
        else:
            self.uni_diff.clear()

    def convertedText(self):
        return self._convertedtext or ''

    def setDocument(self, doc):
        v = documentinfo.docinfo(doc).version_string()
        if v:
            self.fromVersion.setText(v)
            self.reason.setText(_("(set in document)"))
        else:
            self.reason.clear()
        self._text = doc.toPlainText()
        self._encoding = doc.encoding() or 'UTF-8'
        self.setConvertedText()
        self.setDiffText()

    def run(self):
        """Runs convert-ly (again)."""
        fromVersion = self.fromVersion.text()
        toVersion = self.toVersion.text()
        if not fromVersion or not toVersion:
            self.messages.setPlainText(_(
                "Both 'from' and 'to' versions need to be set."))
            return
        info = self._info
        command = info.toolcommand('convert-ly')
        command += ['-f', fromVersion, '-t', toVersion, '-']

        self.job = j = job.Job(command, encoding='utf-8')
        if QSettings().value("lilypond_settings/no_translation", False, bool):
            j.environment['LC_MESSAGES'] = 'C'
        else:
            j.environment.pop('LC_MESSAGES', None)
        if platform.system() == "Darwin":
            import macos
            if macos.inside_app_bundle():
                j.environment['PYTHONPATH'] = None
                j.environment['PYTHONHOME'] = None

        j.done.connect(self.slotJobDone)
        app.job_queue().add_job(j, 'generic')
        j._process.write(self._text.encode('utf-8'))
        j._process.closeWriteChannel()

    def slotJobDone(self):
        j = self.job
        if not j.success and j.failed_to_start():
            self.messages.setPlainText(_(
                "Could not start {convert_ly}:\n\n"
                "{message}\n").format(convert_ly = j.command[0],
                    message = j.error))
            return
        out = j.stdout()
        err = j.stderr()
        self.messages.setPlainText(err)
        self.setConvertedText(out)
        self.setDiffText(out)
        if not out or self._convertedtext == self._text:
            self.messages.append('\n' + _("The document has not been changed."))

    def saveFile(self):
        """Save content in tab as file"""
        tabdata = self.getTabData(self.tabw.currentIndex())
        doc = self.mainwindow.currentDocument()
        orgname = doc.url().toLocalFile()
        filename = os.path.splitext(orgname)[0] + '['+tabdata.filename+']'+'.'+tabdata.ext
        caption = app.caption(_("dialog title", "Save File"))
        filetypes = f'{_("Text Files")} (*.txt);;{_("HTML Files")} (*.htm);;{_("All Files")} (*)'
        filename = QFileDialog.getSaveFileName(self.mainwindow, caption, filename, filetypes)[0]
        if not filename:
            return False # cancelled
        with open(filename, 'wb') as f:
            f.write(tabdata.text.encode('utf-8'))

    def getTabData(self, index):
        """Get content of current tab from current index"""
        if index == 0:
            return FileInfo('message', 'txt', self.messages.toPlainText())
        elif index == 1:
            return FileInfo('html-diff', 'html', self.diff.toHtml())
        elif index == 2:
            return FileInfo('uni-diff', 'diff', self.uni_diff.toPlainText())

    def diffHighl(self, difflist):
        """Return highlighted version of input."""
        result = []
        for l in difflist:
            if l.startswith('-'):
                s = '<span style="color: red; white-space: pre-wrap;">'
            elif l.startswith('+'):
                s = '<span style="color: green; white-space: pre-wrap;">'
            else:
                s = '<span style="white-space: pre-wrap;">'
            h = l.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            result.append(s + h + '</span>')
        return '<br>'.join(result)


class FileInfo():
    """Holds information useful for the file saving"""
    def __init__(self, filename, ext, text):
        self.filename = filename
        self.ext = ext
        self.text = text
