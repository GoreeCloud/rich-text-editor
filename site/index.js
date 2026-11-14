// Optional GoreeCloud source-preview redirect to the independent public repo.
// This does not collect analytics, proxy downloads, or contact Quiet.md hosts.
const TARGET = "https://github.com/GoreeCloud/notes";

export default {
  fetch() {
    // 302 临时跳转，保留日后恢复官网的余地（要永久可改成 301）。
    return Response.redirect(TARGET, 302);
  },
};
