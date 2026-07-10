#!/usr/bin/env python3
"""把封面图片 + 一条文字消息发到飞书。复用 feishu-video-send 的凭证与发送helper。
用法:
  python3 send_images.py --text "标题/链接/标签" --images a.png b.png [--receive-id <id> --receive-id-type open_id]
流程: tenant_access_token -> im/v1/images(上传拿 image_key) -> im/v1/messages(msg_type=image)
"""
import sys, os, argparse

VS = os.path.expanduser("~/.claude/skills/feishu-video-send/scripts")
sys.path.insert(0, VS)
import send_to_feishu as F  # 复用 load_creds/get_token/_multipart/_request/send_message/BASE


def upload_image(token, path):
    body, ct = F._multipart({"image_type": "message"}, "image",
                            os.path.basename(path), open(path, "rb").read(), "image/png")
    r = F._request("POST", f"{F.BASE}/im/v1/images",
                   headers={"Authorization": f"Bearer {token}", "Content-Type": ct}, data=body)
    if r.get("code") != 0:
        F.die(f"上传图片失败: code={r.get('code')} msg={r.get('msg')}")
    return r["data"]["image_key"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default="", help="先发的文字消息(标题/文档链接/标签)")
    ap.add_argument("--images", nargs="*", default=[], help="封面图片路径(按序发)")
    ap.add_argument("--receive-id", default="")
    ap.add_argument("--receive-id-type", default="")
    args = ap.parse_args()

    app_id, app_secret, def_recv, def_type = F.load_creds()
    recv = args.receive_id or def_recv
    recv_type = args.receive_id_type or def_type or "open_id"
    if not recv:
        F.die("缺少接收方: 设 FEISHU_DEFAULT_RECEIVE_ID / config.json default_receive_id 或传 --receive-id")
    token = F.get_token(app_id, app_secret)

    if args.text:
        F.send_message(token, recv, recv_type, "text", {"text": args.text})
        print("✓ 文字消息已发")
    for p in args.images:
        if not os.path.exists(p):
            print(f"⚠ 跳过不存在: {p}"); continue
        key = upload_image(token, p)
        F.send_message(token, recv, recv_type, "image", {"image_key": key})
        print(f"✓ 封面已发: {os.path.basename(p)}")
    print("DONE")


if __name__ == "__main__":
    main()
