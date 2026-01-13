"""
Example Data for tests
"""


DIR = '/dls/science/groups/das/ExampleData/hdfmap_tests/'
FILES = [
    (DIR + 'i16/777777.nxs', 'i16 pilatus eta scan, tiff files, no defaults'),
    (DIR + 'i16/1040311.nxs', 'i16 pilatus eta scan, old nexus format'),
    (DIR + 'i16/1040323.nxs', 'i16 pilatus hkl scan, new nexus format'),
    (DIR + 'i16/982681.nxs', 'i16 pil2m single point scan'),
    (DIR + 'i16/928878.nxs', 'i16 merlin 2d delta gam calibration'),
    (DIR + 'i16/1109527.nxs', 'i16 pilatus eta scan, new nexus format'),
    (DIR + 'i16/1116988.nxs', 'i16 pilatus eta scan, new nexus format2'),
    (DIR + 'i16/processed/1090391_msmapper.nxs', 'msmapper volume'),
    (DIR + 'i16/processed/1109527_msmapper.nxs', 'msmapper volume 527'),
    (DIR + 'i16/processed/1116988_msmapper.nxs', 'msmapper volume 988'),
    (DIR + 'i10/i10-608314.nxs', 'i10 pimte scan'),
    (DIR + 'i10/i10-618365.nxs', 'i10 scan'),
    (DIR + 'i10/i10-854741.nxs', 'i10 pimte scan, single point with TIFF'),
    (DIR + 'i10/i10-921636.nxs', 'i10 pimte new scan'),
    (DIR + 'i10/i10-1-207.nxs', 'i10-1 scan'),
    (DIR + 'i10/i10-1-10.nxs', 'i10-1 XASscan example'),
    (DIR + 'i10/i10-1-26851.nxs', 'i10-1 XASscan example'),
    (DIR + 'i10/i10-1-28428.nxs', 'i10-1 3D hysteresis example'),
    (DIR + 'i10/i10-1-37436_xas_notebook.nxs', 'i10-1 XASproc example'),
    (DIR + 'i06/i06-1-302762.nxs', 'i06 scan'),
    (DIR + 'i06/i06-1-366107.nxs', 'i06 hkl scan'),
    (DIR + 'i06/i06-1-372210.nxs', 'i06-1 zacscan'),
    (DIR + 'i21/i21-157111.nxs', 'i21 xcam single point scan'),
    (DIR + 'i21/i21-157116.nxs', 'i21 xcam multi point scan'),
    (DIR + 'i13/i13-1-368910.nxs', 'i13 Excalibur axis scan'),
    (DIR + 'i18/i18-218770.nxs', 'i18 example'),
    (DIR + 'i07/i07-537190.nxs', 'i07 example'),
    (DIR + 'i09/i09-279773.nxs', 'i09 example'),
    (DIR + 'nxxas/KEK_PFdata.h5', 'NXxas example from KEK'),
]
FILES_DICT = {
    desc: path for path, desc in FILES
}

