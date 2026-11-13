import CoreGraphics
let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly], kCGNullWindowID) as! [[String: Any]]
for w in list where (w["kCGWindowOwnerName"] as? String ?? "").contains("goreecloud_rich_text_editor") { print(w["kCGWindowNumber"]!) }
