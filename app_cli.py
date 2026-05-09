import argparse
from audioasset_creator import save


def main():
    parser = argparse.ArgumentParser(description="Audio Asset Creator CLI")
    parser.add_argument("file", help="Path to an audio file")
    args = parser.parse_args()

    out = save(args.file)
    print(f"Asset saved: {out}")


if __name__ == "__main__":
    main()
