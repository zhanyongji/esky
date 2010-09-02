"""

    esky.bdist_esky.pypyc:  support for compiling bootstrap exes with PyPy


This module provides the supporting code to compile bootstrapping exes with
PyPy.  In theory, this should provide for faster startup and less resource
usage than building the bootstrap exes out of the frozen application stubs.

"""

import os
import sys

import pypy.translator.goal.translate



def compile_rpython(infile,outfile,gui_only=False,static_msvcrt=False):
    """Compile the given RPython input file to executable output file."""
    orig_argv = sys.argv[:]
    try:
        sys.argv[0] = sys.executable
        sys.argv[1:] = ["--output",outfile,"--batch","--gc=ref",]
        sys.argv.append(infile)
        pypy.translator.goal.translate.main()
    finally:
        sys.argv = orig_argv



#  For win32, we need some fancy features not provided by the normal
#  PyPy compiler.  Fortunately we csan hack them in.
#
if sys.platform == "win32":
  import pypy.translator.platform.windows
  class CustomWin32Platform(pypy.translator.platform.windows.MsvcPlatform):
      """Custom PyPy platform object with fancy windows features.

      This platform knows how to do two things that native PyPy cannot -
      build a windows-only executable, and statically link the C runtime.
      Unfortunately there's a fair amount of monkey-patchery involved.
      """

      gui_only = False
      static_msvcrt = False

      def _compile_c_file(self,cc,cfile,compile_args):
          #  Add stub code for WinMain to gui-only compiles.
          if self.gui_only:
              with open(str(cfile),"r+b") as f:
                  f.seek(0,os.SEEK_END)
                  f.write(WINMAIN_STUB)
          return super(CustomWin32Platform,self)._compile_c_file(cc,cfile,compile_args)

      def _link(self,cc,ofiles,link_args,standalone,exe_name):
          print "LINK", ofiles
          #  Link against windows subsystem if gui-only is specified.
          if self.gui_only:
              link_args.append("/subsystem:windows")
          #  Choose whether to link crt statically or dynamically.
          if not self.static_msvcrt:
              if "/MT" in self.cflags:
                  self.cflags.remove("/MT")
              if "/MD" not in self.cflags:
                  self.cflags.append("/MD")
          else:
              if "/MD" in self.cflags:
                  self.cflags.remove("/MD")
              if "/MT" not in self.cflags:
                  self.cflags.append("/MT")
              #  Static linking means no manifest is generated.
              #  Create a fake one so PyPy doesn't get confused.
              if self.version >= 80:
                  ofile = ofiles[-1]
                  manifest = str(ofile.dirpath().join(ofile.purebasename))
                  manifest += '.manifest'
                  with open(manifest,"w") as mf:
                      mf.write(DUMMY_MANIFEST)
          return super(CustomWin32Platform,self)._link(cc,ofiles,link_args,standalone,exe_name)

      def _finish_linking(self,ofiles,*args,**kwds):
          print "FINISH LINKING", ofiles
          return super(CustomWin32Platform,self)._finish_linking(ofiles,*args,**kwds)

  pypy.translator.platform.platform = CustomWin32Platform()
  pypy.translator.platform.host = pypy.translator.platform.platform
  pypy.translator.platform.host_factory = lambda *a: pypy.translator.platform.platform




WINMAIN_STUB = """
#ifndef PYPY_NOT_MAIN_FILE

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

int WINAPI WinMain(HINSTANCE hInstance,HINSTANCE hPrevInstance,
                   LPWSTR lpCmdLine,int nCmdShow) {
    return main(__argc, __argv);
}
#endif
"""

DUMMY_MANIFEST =  """
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
</assembly>
"""
