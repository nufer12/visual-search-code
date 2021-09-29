from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

ext_modules = [Extension("voting_cython",
              ["voting_cython.pyx"],
              libraries=["m"],
              extra_compile_args=["-ffast-math"])]

setup(
  name="voting_cython",
  cmdclass={"build_ext": build_ext},
  ext_modules=ext_modules
)
