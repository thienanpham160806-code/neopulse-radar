import { redirect } from "next/navigation";

/** Giữ các liên kết đăng nhập cũ hoạt động sau khi bỏ mật khẩu. */
export default function LoginPage() {
  redirect("/");
}
