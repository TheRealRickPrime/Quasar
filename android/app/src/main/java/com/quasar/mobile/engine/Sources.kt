package com.quasar.mobile.engine

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import androidx.documentfile.provider.DocumentFile
import java.io.IOException
import java.io.OutputStream

class PickedSource(val uri: Uri, val name: String, val isFolder: Boolean)

object Sources {
    fun describe(ctx: Context, uri: Uri, isFolder: Boolean): PickedSource {
        val name = if (isFolder) {
            DocumentFile.fromTreeUri(ctx, uri)?.name ?: "folder"
        } else {
            ctx.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use {
                if (it.moveToFirst()) it.getString(0) else null
            } ?: "file"
        }
        return PickedSource(uri, name, isFolder)
    }

    private fun fileSize(ctx: Context, uri: Uri): Long {
        val q = ctx.contentResolver.query(uri, arrayOf(OpenableColumns.SIZE), null, null, null)?.use {
            if (it.moveToFirst() && !it.isNull(0)) it.getLong(0) else null
        }
        if (q != null) return q
        // Size unknown: measure by reading once.
        return ctx.contentResolver.openInputStream(uri)?.use { s ->
            val b = ByteArray(64 * 1024); var t = 0L
            while (true) { val n = s.read(b); if (n < 0) break; t += n }
            t
        } ?: 0L
    }

    fun collect(ctx: Context, sources: List<PickedSource>): List<SourceEntry> {
        val out = ArrayList<SourceEntry>()
        val used = HashSet<String>()
        for (s in sources) {
            if (s.isFolder) {
                val root = DocumentFile.fromTreeUri(ctx, s.uri) ?: continue
                walk(ctx, root, uniqueName(used, s.name), out)
            } else {
                val uri = s.uri
                out += SourceEntry(uniqueName(used, s.name), fileSize(ctx, uri)) { open(ctx, uri) }
            }
        }
        return out
    }

    private fun uniqueName(used: MutableSet<String>, name: String): String {
        var n = name; var i = 1
        while (!used.add(n)) n = "${i++}_$name"
        return n
    }

    private fun walk(ctx: Context, dir: DocumentFile, prefix: String, out: MutableList<SourceEntry>) {
        for (f in dir.listFiles()) {
            val name = f.name ?: continue
            if (f.isDirectory) walk(ctx, f, "$prefix/$name", out)
            else if (f.isFile) {
                val uri = f.uri
                out += SourceEntry("$prefix/$name", f.length()) { open(ctx, uri) }
            }
        }
    }

    private fun open(ctx: Context, uri: Uri) =
        ctx.contentResolver.openInputStream(uri) ?: throw IOException("Cannot open $uri")
}

/** Creates files (and subfolders) below a user-chosen SAF folder. */
class TreeWriter(private val ctx: Context, treeUri: Uri) {
    private val root = DocumentFile.fromTreeUri(ctx, treeUri) ?: throw IOException("Cannot open the output folder")
    private val dirs = HashMap<String, DocumentFile>()

    private fun dir(path: String): DocumentFile {
        if (path.isEmpty()) return root
        return dirs.getOrPut(path) {
            val parent = dir(path.substringBeforeLast('/', ""))
            val name = path.substringAfterLast('/')
            parent.findFile(name)?.takeIf { it.isDirectory } ?: parent.createDirectory(name)
                ?: throw IOException("Cannot create folder $name")
        }
    }

    fun open(path: String, mime: String = "application/octet-stream"): OutputStream {
        val parent = dir(path.substringBeforeLast('/', ""))
        val name = path.substringAfterLast('/')
        parent.findFile(name)?.let {
            if (it.isDirectory || !it.delete()) throw IOException("Cannot replace $name; choose an empty folder")
        }
        val f = parent.createFile(mime, name) ?: throw IOException("Cannot create $name")
        return ctx.contentResolver.openOutputStream(f.uri) ?: throw IOException("Cannot write $name")
    }
}
