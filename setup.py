from distutils.core import setup, Extension

module1 = Extension('cpp_modules',
                    sources = ['cpp_modules/cppmodules.cc'],
                    )

setup(name = 'cpp_modules', version = '1.0.0',  \
   ext_modules = [module1])