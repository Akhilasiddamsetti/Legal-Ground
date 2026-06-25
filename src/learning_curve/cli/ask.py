import argparse
from pathlib import Path

from learning_curve.web.runtime import build_live_runtime, build_principal


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the deposition-prep assistant.")
    parser.add_argument("question")
    parser.add_argument("--role", default="pilot_user")
    parser.add_argument("--matter", default="acme-v-northridge")
    parser.add_argument("--user", default="local-cli")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--corpus-dir", help="Case root for single-case mode, or portfolio root when used with --all-cases.")
    parser.add_argument("--all-cases", action="store_true", help="Load all professional case folders under the portfolio root.")
    parser.add_argument("--aws-region")
    parser.add_argument("--aws-profile")
    parser.add_argument("--bedrock-model")
    args = parser.parse_args()

    runtime = build_live_runtime(
        top_k=args.top_k,
        corpus_dir=Path(args.corpus_dir) if args.corpus_dir else None,
        all_cases=args.all_cases,
        aws_region=args.aws_region,
        aws_profile=args.aws_profile,
        bedrock_model=args.bedrock_model,
        default_user_id=args.user,
    )
    principal = build_principal(args.matter, args.role, user_id=args.user)
    answer = runtime.assistant.answer(args.question, principal, log_dir=runtime.log_dir)

    print(answer.text)
    if answer.citations:
        print("\nSources:")
        for citation in answer.citations:
            print(f"  [{citation['marker']}] {citation['display_text']}")
    elif answer.abstained:
        print("\n(abstained - insufficient evidence in approved documents)")


if __name__ == "__main__":
    main()
