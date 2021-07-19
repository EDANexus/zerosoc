import argparse
import siliconcompiler as sc
import os

from sources import add_sources

def configure_general(chip, start, stop):
    # Prevent us from erroring out on lint warnings during import
    chip.set('relax', 'true')

    # hack to work around fact that $readmemh now runs in context of build
    # directory and can't load .mem files using relative paths
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    chip.add('define', f'MEM_ROOT={cur_dir}')

    add_sources(chip)

    chip.set('start', start)
    chip.set('stop', stop)

def configure_asic_freepdk45(chip):
    chip.add('design', 'top_asic')

    chip.set('target', f'freepdk45_asic-sv2v')
    chip.add('define', f'PRIM_DEFAULT_IMPL="prim_pkg::ImplFreePdk45"')

    chip.add('source', 'hw/top_asic.v')
    chip.add('source', 'oh/padring/hdl/oh_padring.v')
    chip.add('source', 'oh/padring/hdl/oh_pads_corner.v')
    chip.add('source', 'oh/padring/hdl/oh_pads_domain.v')

    chip.add('source', 'asic/asic_iobuf.v')
    chip.add('source', 'asic/asic_iocut.v')
    chip.add('source', 'asic/asic_iopoc.v')
    chip.add('source', 'asic/asic_iovdd.v')
    chip.add('source', 'asic/asic_iovddio.v')
    chip.add('source', 'asic/asic_iovss.v')
    chip.add('source', 'asic/asic_iovssio.v')

    chip.add('source', 'asic/bb_iocell.v')

    # need to include IOPAD blackbox since we don't have a lib file for iocells.lef
    chip.add('source', 'asic/iopad.v')

    chip.set('asic', 'floorplan', 'asic/floorplan.py')

    macro = 'sram_32x2048_1rw'
    chip.add('asic', 'macrolib', macro)
    chip.add('macro', macro, 'model', 'typical', 'nldm', 'lib', f'hw/prim/{target.lower()}/{macro}.lib')
    chip.add('macro', macro, 'lef', f'hw/prim/{target.lower()}/{macro}.lef')
    chip.set('macro', macro, 'cells', 'ram', 'sram_32x2048_1rw')
    chip.add('source', 'hw/prim/freepdk45/prim_freepdk45_ram_1p.v')
    chip.add('source', 'hw/prim/freepdk45/sram_32x2048_1rw.bb.v')

    macro = 'io'
    chip.add('asic', 'macrolib', macro)
    chip.set('macro', macro, 'lef', f'asic/iocells.lef')
    chip.set('macro', macro, 'cells', 'gpio', 'IOPAD')
    chip.set('macro', macro, 'cells', 'vdd', 'PWRPAD')
    chip.set('macro', macro, 'cells', 'vddio', 'PWRPAD')
    chip.set('macro', macro, 'cells', 'vss', 'PWRPAD')
    chip.set('macro', macro, 'cells', 'vssio', 'PWRPAD')
    chip.set('macro', macro, 'cells', 'corner', 'CORNER')
    chip.set('macro', macro, 'cells', 'fill1',  'FILLER01')
    chip.set('macro', macro, 'cells', 'fill2',  'FILLER02')
    chip.set('macro', macro, 'cells', 'fill5',  'FILLER05')
    chip.set('macro', macro, 'cells', 'fill10', 'FILLER10')
    chip.set('macro', macro, 'cells', 'fill25', 'FILLER25')
    chip.set('macro', macro, 'cells', 'fill50', 'FILLER50')

def configure_asic_sky130(chip):
    chip.add('design', 'zerosoc')

    chip.set('target', f'skywater130_asic-sv2v')
    chip.add('define', f'PRIM_DEFAULT_IMPL="prim_pkg::ImplSky130"')

    chip.set('asic', 'diesize', '0 0 2580.2 2542.4')
    chip.set('asic', 'coresize', '150.1 151.2 2430.1 2391.2')

    macro = 'ram'
    chip.add('asic', 'macrolib', macro)
    chip.add('macro', macro, 'model', 'typical', 'nldm', 'lib', 'asic/sky130/sky130_sram_2kbyte_1rw1r_32x512_8_TT_1p8V_25C.lib')
    chip.add('macro', macro, 'lef', 'asic/sky130/sky130_sram_2kbyte_1rw1r_32x512_8.lef')
    chip.add('macro', macro, 'gds', 'asic/sky130/sky130_sram_2kbyte_1rw1r_32x512_8.gds')
    chip.set('macro', macro, 'cells', 'ram', 'sky130_sram_2kbyte_1rw1r_32x512_8')
    chip.add('source', 'hw/prim/sky130/prim_sky130_ram_1p.v')
    chip.add('source', 'asic/sky130/sky130_sram_2kbyte_1rw1r_32x512_8.bb.v')

def configure_asic(chip, target):
    chip.set('constraint', 'asic/constraints.sdc')

    if target == 'freepdk45':
        configure_asic_freepdk45(chip)
    elif target == 'sky130':
        configure_asic_sky130(chip)
    else:
        raise ValueError('Invalid target')

def configure_fpga(chip):
    chip.add('design', 'top_icebreaker')

    chip.add('source', 'hw/top_icebreaker.v')
    chip.set('target', 'ice40_nextpnr')
    chip.set('constraint', 'fpga/icebreaker.pcf')

def main():
    parser = argparse.ArgumentParser(description='Build ZeroSoC')
    parser.add_argument('--fpga', action='store_true', default=False, help='Build for ice40 FPGA (build ASIC by default)')
    parser.add_argument('-a', '--start', default='import', help='Start step')
    parser.add_argument('-z', '--stop', default='export', help='Stop step')
    parser.add_argument('-t', '--target', default='freepdk45', help='ASIC target ("freepdk45" or "sky130")')
    options = parser.parse_args()

    chip = sc.Chip()
    configure_general(chip, options.start, options.stop)

    if options.fpga:
        configure_fpga(chip)
    else:
        configure_asic(chip, options.target)

    chip.set_jobid()
    chip.target()

    # TODO: hack - CTS currently doesn't work
    if not options.fpga:
        chip.cfg['steplist']['value'].remove('cts')

    chip.run()

    chip.summary()

if __name__ == '__main__':
    main()
