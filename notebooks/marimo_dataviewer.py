import marimo

__generated_with = "0.18.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import matplotlib.pyplot as plt
    from mmg_toolbox import Experiment, version_info
    from mmg_toolbox.fitting import poisson_errors

    print(version_info())
    return Experiment, mo, plt


@app.cell
def _(Experiment, mo):
    cli_args = mo.cli_args()
    datadir = cli_args.get('datadir', r"D:\I16_Data\mm22052-1")
    beamline = cli_args.get('beamline', 'i16')
    exp = Experiment(datadir, instrument=beamline)
    print(exp)
    return (exp,)


@app.cell
def _(exp, mo):
    scan_list = list(exp.scan_list)
    scanno = mo.ui.number(start=scan_list[0], stop=scan_list[-1], label='Scan Number')
    return (scanno,)


@app.cell
def _(exp, mo, scanno):
    mo.hstack([
        scanno, 
        mo.md(f"Has value: {scanno.value}"), 
        mo.md(f"File: {exp.scan_list.get(scanno.value, 'No File')}")
    ])
    return


@app.cell
def _(exp, scanno):
    if scanno.value in exp.scan_list:
        scan = exp.scan(scanno.value)
        print(scan)
    else:
        scan = None
    return (scan,)


@app.cell
def _(plt, scan):
    if scan:
        scan.plot()
        plt.show()
    return


@app.cell
def _(plt, scan):
    if scan:
        result = scan.fit(model='pVoight')
        result.plot()
        plt.show()
    else:
        result = None

    return (result,)


@app.cell
def _(result):
    if result:
        print(result)
    return


@app.cell
def _(scan):
    if scan and scan.map.image_data:
        scan.plot.image();
    
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
