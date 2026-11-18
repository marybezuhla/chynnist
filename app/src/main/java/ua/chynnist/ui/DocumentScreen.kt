package ua.chynnist.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.LinkAnnotation
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextLinkStyles
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.BaselineShift
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.isSpecified
import ua.chynnist.R
import ua.chynnist.text.Align
import ua.chynnist.text.Block
import ua.chynnist.text.Cell
import ua.chynnist.text.Mark
import ua.chynnist.text.Para
import ua.chynnist.text.Reading

/** The items above the text in the list: the document's head. */
const val HEAD_ITEMS = 1

/**
 * A document to read: its title and state on top, the text, and a bar with the place in the text and the
 * size of the letters. The text can be selected and copied.
 */
@Composable
fun DocumentScreen(
    reading: Reading,
    names: Names,
    test: Boolean,
    scale: Float,
    onScale: (Float) -> Unit,
    list: LazyListState,
    jump: String?,
    onJumped: () -> Unit,
    onLink: (String) -> Unit,
    onToc: () -> Unit,
    onBack: () -> Unit,
) {
    val scheme = MaterialTheme.colorScheme
    // A place asked for (from the contents or a link) is brought to the top
    LaunchedEffect(jump) {
        if (jump != null) {
            reading.anchorBlock[jump]?.let { list.scrollToItem(it + HEAD_ITEMS) }
            onJumped()
        }
    }
    val place by remember(reading) { derivedStateOf { reading.place(maxOf(0, list.firstVisibleItemIndex - HEAD_ITEMS)) } }
    Scaffold(
        containerColor = scheme.background,
        topBar = {
            // The title is the first thing in the text itself (whole, at any font size); the bar holds the actions
            Bar("", onBack) {
                if (reading.toc.isNotEmpty()) {
                    IconButton(onClick = onToc) { Icon(painterResource(R.drawable.ic_toc), contentDescription = stringResource(R.string.toc)) }
                }
            }
        },
        bottomBar = {
            ReadingBar(
                place = place?.let { stringResource(R.string.place_of, it.short, it.number, it.of) },
                scale = scale,
                onScale = onScale,
                onPlace = onToc,
            )
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.TopCenter) {
            val links = TextLinkStyles(SpanStyle(color = scheme.primary, textDecoration = TextDecoration.Underline))
            SelectionContainer {
                LazyColumn(
                    Modifier.widthIn(max = READING_WIDTH).fillMaxWidth(),
                    state = list,
                    contentPadding = PaddingValues(start = 20.dp, end = 20.dp, top = 8.dp, bottom = 32.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    item(key = "head") { Head(reading, names, test, scale) }
                    itemsIndexed(reading.blocks) { i, block ->
                        when (block) {
                            is Block.Text -> Paragraph(block.para, reading.entryLevel[i], reading.finest, scale, links, onLink)
                            is Block.Table -> Table(block, scale, links, onLink)
                            is Block.Rule -> HorizontalDivider(Modifier.padding(vertical = 8.dp), color = scheme.outlineVariant)
                        }
                    }
                }
            }
        }
    }
}

private fun TextStyle.scaled(scale: Float) = copy(
    fontSize = if (fontSize.isSpecified) fontSize * scale else fontSize,
    lineHeight = if (lineHeight.isSpecified) lineHeight * scale else lineHeight,
)

@Composable
private fun Head(reading: Reading, names: Names, test: Boolean, scale: Float) {
    val scheme = MaterialTheme.colorScheme
    Column(Modifier.fillMaxWidth().padding(bottom = 8.dp), verticalArrangement = Arrangement.spacedBy(6.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            reading.title,
            style = MaterialTheme.typography.titleLarge.scaled(scale),
            fontWeight = FontWeight.SemiBold,
            color = scheme.onBackground,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth().semantics { heading() },
        )
        val state = listOfNotNull(
            reading.status?.let { names.of("status", it) },
            reading.edition?.let { stringResource(R.string.edition_of, showDate(it)) },
        ).joinToString(" · ")
        if (state.isNotEmpty()) Text(state, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold, color = scheme.onSurface, textAlign = TextAlign.Center)
        reading.number?.let { Text(stringResource(R.string.number_of, it), style = MaterialTheme.typography.bodySmall, color = scheme.onSurfaceVariant) }
        Text(stringResource(R.string.not_official_short), style = MaterialTheme.typography.bodySmall, color = scheme.onSurfaceVariant, textAlign = TextAlign.Center)
        if (test) {
            Surface(shape = RoundedCornerShape(10.dp), color = scheme.errorContainer) {
                Text(stringResource(R.string.test_data), style = MaterialTheme.typography.bodySmall, color = scheme.onErrorContainer,
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp))
            }
        }
        HorizontalDivider(Modifier.padding(top = 6.dp), color = scheme.outlineVariant)
    }
}

/** One paragraph's text with its looks and links. */
fun annotated(para: Para, links: TextLinkStyles, onLink: (String) -> Unit): AnnotatedString = buildAnnotatedString {
    append(para.text)
    for (m in para.marks) {
        val style = when (m.mark) {
            Mark.BOLD -> SpanStyle(fontWeight = FontWeight.Bold)
            Mark.ITALIC -> SpanStyle(fontStyle = FontStyle.Italic)
            Mark.UNDERLINE -> SpanStyle(textDecoration = TextDecoration.Underline)
            Mark.STRIKE -> SpanStyle(textDecoration = TextDecoration.LineThrough)
            Mark.SUP -> SpanStyle(baselineShift = BaselineShift.Superscript, fontSize = 0.7.em)
            Mark.SUB -> SpanStyle(baselineShift = BaselineShift.Subscript, fontSize = 0.7.em)
            Mark.SMALL -> SpanStyle(fontSize = 0.85.em)
            Mark.CODE -> SpanStyle(fontFamily = FontFamily.Monospace)
        }
        addStyle(style, m.start, m.end)
    }
    for (l in para.links) addLink(LinkAnnotation.Clickable(l.href, links) { onLink(l.href) }, l.start, l.end)
}

/**
 * A paragraph. One that starts an entry of the contents is a heading for TalkBack; the larger parts (sections,
 * chapters: entries above the finest level) also look like headings. Editorial notes {…} are smaller and quieter.
 */
@Composable
private fun Paragraph(para: Para, entry: Int?, finest: Int, scale: Float, links: TextLinkStyles, onLink: (String) -> Unit) {
    val scheme = MaterialTheme.colorScheme
    val part = (entry != null && entry < finest) || para.heading in 1..3
    val style = when {
        part -> MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold, textAlign = TextAlign.Center)
        para.note -> MaterialTheme.typography.bodySmall
        para.pre -> MaterialTheme.typography.bodyMedium.copy(fontFamily = FontFamily.Monospace)
        else -> MaterialTheme.typography.bodyLarge
    }.let {
        when (para.align) {
            Align.CENTER -> it.copy(textAlign = TextAlign.Center)
            Align.END -> it.copy(textAlign = TextAlign.End)
            Align.START -> it
        }
    }.scaled(scale)
    val text = remember(para, links) { annotated(para, links, onLink) }
    Text(
        text,
        style = style,
        color = if (para.note) scheme.onSurfaceVariant else scheme.onBackground,
        modifier = Modifier.fillMaxWidth()
            .padding(top = if (part) 12.dp else 0.dp)
            .then(if (entry != null || para.heading > 0) Modifier.semantics { heading() } else Modifier),
    )
}

/** A table: cells side by side with thin lines between; wider than the screen, it scrolls sideways. */
@Composable
private fun Table(table: Block.Table, scale: Float, links: TextLinkStyles, onLink: (String) -> Unit) {
    val scheme = MaterialTheme.colorScheme
    val columns = table.rows.maxOf { row -> row.sumOf { it.colspan } }
    BoxWithConstraints(Modifier.fillMaxWidth()) {
        val width = maxOf(maxWidth, MIN_COLUMN * columns * scale)
        Box(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState())) {
            Column(Modifier.width(width).border(BorderStroke(1.dp, scheme.outlineVariant))) {
                for (row in table.rows) {
                    Row(Modifier.fillMaxWidth().height(IntrinsicSize.Min)) {
                        for (cell in row) TableCell(cell, scale, links, onLink, Modifier.weight(cell.colspan.toFloat()))
                        val missing = columns - row.sumOf { it.colspan }
                        if (missing > 0) Box(Modifier.weight(missing.toFloat()))
                    }
                }
            }
        }
    }
}

private val MIN_COLUMN = 120.dp

@Composable
private fun TableCell(cell: Cell, scale: Float, links: TextLinkStyles, onLink: (String) -> Unit, modifier: Modifier) {
    val scheme = MaterialTheme.colorScheme
    Column(
        modifier.fillMaxHeight().border(BorderStroke(0.5.dp, scheme.outlineVariant)).padding(6.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        for (para in cell.paras) {
            val base = MaterialTheme.typography.bodySmall.let { if (cell.header) it.copy(fontWeight = FontWeight.SemiBold) else it }
            val style = when (para.align) {
                Align.CENTER -> base.copy(textAlign = TextAlign.Center)
                Align.END -> base.copy(textAlign = TextAlign.End)
                Align.START -> base
            }.scaled(scale)
            val text = remember(para, links) { annotated(para, links, onLink) }
            Text(text, style = style, color = scheme.onBackground, modifier = Modifier.fillMaxWidth())
        }
    }
}

/** The place in the text (a tap opens the contents) and the size of the letters. */
@Composable
private fun ReadingBar(place: String?, scale: Float, onScale: (Float) -> Unit, onPlace: () -> Unit) {
    val scheme = MaterialTheme.colorScheme
    Surface(color = scheme.surface) {
        Column {
            HorizontalDivider(color = scheme.outlineVariant)
            Row(
                Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                val smaller = stringResource(R.string.text_smaller)
                val larger = stringResource(R.string.text_larger)
                OutlinedButton(
                    onClick = { onScale(maxOf(ReadingStore.MIN_SCALE, scale - ReadingStore.SCALE_STEP)) },
                    enabled = scale > ReadingStore.MIN_SCALE + 0.01f,
                    modifier = Modifier.heightIn(min = 48.dp).semantics { contentDescription = smaller },
                ) { Text(stringResource(R.string.text_smaller_short), modifier = Modifier.clearAndSetSemantics { }) }
                OutlinedButton(
                    onClick = { onScale(minOf(ReadingStore.MAX_SCALE, scale + ReadingStore.SCALE_STEP)) },
                    enabled = scale < ReadingStore.MAX_SCALE - 0.01f,
                    modifier = Modifier.heightIn(min = 48.dp).semantics { contentDescription = larger },
                ) { Text(stringResource(R.string.text_larger_short), modifier = Modifier.clearAndSetSemantics { }) }
                Box(
                    Modifier.weight(1f).heightIn(min = 48.dp).then(if (place != null) Modifier.clickable(onClick = onPlace) else Modifier),
                    contentAlignment = Alignment.CenterEnd,
                ) {
                    if (place != null) {
                        Text(place, style = MaterialTheme.typography.labelLarge, color = scheme.onSurfaceVariant, maxLines = 2,
                            textAlign = TextAlign.End, modifier = Modifier.padding(horizontal = 8.dp))
                    }
                }
            }
        }
    }
}
