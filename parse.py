from st_hsdatalog.HSD.HSDatalog import HSDatalog

def main() -> None:
    hsd_factory = HSDatalog()

    hsd = hsd_factory.create_hsd("/hd0/lavoro/st-vespucci/acquisitions/mock-dataset/logs/20240212_12_44_00")

    df = hsd.get_dataframe("lsm6dsv16x_acc")

    print(df)

if __name__ == "__main__":
    main()