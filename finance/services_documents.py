import json
from decimal import Decimal
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext as _

from .forms import DocumentForm, DOMAIN_CATEGORY_MAP
from .models import (
    Asset,
    CashFlowSource,
    Document,
    InsurancePolicy,
    Loan,
    OneTimeEvent,
    Pension,
    PhysicalAsset,
    PropertyComponent,
    RealEstate,
)


def extract_pdf_text(file_obj, max_chars=25000):
    """
    Extracts plain text from an uploaded PDF using pypdf (graceful fallback on errors).
    Always resets file pointer to 0 afterwards so FileField can persist the file.
    """
    if not file_obj:
        return ""
    name = getattr(file_obj, 'name', '') or ''
    if not name.lower().endswith('.pdf'):
        return ""
    try:
        from pypdf import PdfReader
        pos = file_obj.tell() if hasattr(file_obj, 'tell') else 0
        file_obj.seek(0)
        reader = PdfReader(file_obj)
        chunks = []
        total_len = 0
        for page in reader.pages[:30]:
            text = (page.extract_text() or '').strip()
            if text:
                chunks.append(text)
                total_len += len(text)
                if total_len >= max_chars:
                    break
        file_obj.seek(pos)
        return "\n".join(chunks)[:max_chars]
    except Exception:
        try:
            file_obj.seek(0)
        except Exception:
            pass
        return ""


def serialize_document(doc):
    """Serializes a Document instance for Alpine.js / JSON template usage."""
    ext = (doc.filename.rsplit('.', 1)[-1].lower() if '.' in doc.filename else '')
    return {
        'id': doc.id,
        'title': doc.title,
        'domain': doc.domain,
        'domain_display': doc.get_domain_display(),
        'category': doc.category,
        'category_display': doc.get_category_display(),
        'related_object_label': doc.related_object_label,
        'real_estate_id': doc.real_estate_id,
        'loan_id': doc.loan_id,
        'insurance_policy_id': doc.insurance_policy_id,
        'pension_id': doc.pension_id,
        'asset_id': doc.asset_id,
        'physical_asset_id': doc.physical_asset_id,
        'date': doc.date.strftime('%Y-%m-%d') if doc.date else '',
        'date_display': doc.date.strftime('%d.%m.%Y') if doc.date else '',
        'amount': float(doc.amount) if doc.amount is not None else None,
        'notes': doc.notes or '',
        'filename': doc.filename,
        'file_size': doc.file_size_display,
        'is_pdf': ext == 'pdf',
        'is_image': ext in {'png', 'jpg', 'jpeg', 'gif', 'webp'},
        'download_url': reverse('finance:document_download', args=[doc.id]),
        'delete_url': reverse('finance:document_delete', args=[doc.id]),
    }


def get_documents_data(user, domains=None):
    """Returns documents and summary metrics for the user, optionally filtered by domains."""
    qs = Document.objects.filter(user=user).select_related(
        'real_estate', 'loan', 'insurance_policy', 'pension', 'asset', 'physical_asset'
    ).order_by('-date', '-uploaded_at')
    if domains:
        qs = qs.filter(domain__in=domains)

    docs = list(qs)
    serialized = [serialize_document(d) for d in docs]
    total_amount = sum((Decimal(str(d.amount or '0.00')) for d in docs if d.amount is not None), Decimal('0.00'))

    domain_counts = {}
    for d in docs:
        domain_counts[d.domain] = domain_counts.get(d.domain, 0) + 1

    return {
        'documents': docs,
        'serialized_documents': serialized,
        'total_count': len(docs),
        'total_amount': total_amount,
        'domain_counts': domain_counts,
    }


def get_document_modal_context(user):
    """Builds form & JSON metadata needed by templates/finance/partials/document_modal.html."""
    domain_objects = {
        'real_estate': [{'id': o.id, 'name': o.name} for o in RealEstate.objects.filter(user=user).order_by('name')],
        'loan': [{'id': o.id, 'name': o.name} for o in Loan.objects.filter(user=user).order_by('name')],
        'insurance': [{'id': o.id, 'name': o.name} for o in InsurancePolicy.objects.filter(user=user).order_by('name')],
        'pension': [{'id': o.id, 'name': o.provider} for o in Pension.objects.filter(user=user).order_by('provider')],
        'asset': [{'id': o.id, 'name': o.name} for o in Asset.objects.filter(user=user).order_by('name')],
        'physical_asset': [{'id': o.id, 'name': o.name} for o in PhysicalAsset.objects.filter(user=user).order_by('name')],
        'general': [],
    }
    category_labels = {code: str(label) for code, label in Document.CATEGORY_CHOICES}
    domain_categories = {
        dom: [{'value': c, 'label': category_labels.get(c, c)} for c in cats]
        for dom, cats in DOMAIN_CATEGORY_MAP.items()
    }
    return {
        'document_form': DocumentForm(user=user),
        'doc_domain_choices': Document.DOMAIN_CHOICES,
        'doc_category_choices': Document.CATEGORY_CHOICES,
        'doc_domain_objects_json': json.dumps(domain_objects),
        'doc_domain_categories_json': json.dumps(domain_categories),
    }


def search_all_user_data(user, query='', scope='all'):
    """
    Searches across all 5 user financial domains (strictly isolated by user):
    - documents (including extracted_text from PDFs)
    - real_estate_loans (RealEstate, Loan, PropertyComponent)
    - insurance_pensions (InsurancePolicy, Pension)
    - assets (Asset, PhysicalAsset)
    - cashflows (CashFlowSource, OneTimeEvent)
    """
    q = (query or '').strip()

    def matches_scope(target):
        return scope in ('all', target)

    # 1. Documents
    docs_qs = Document.objects.filter(user=user).select_related(
        'real_estate', 'loan', 'insurance_policy', 'pension', 'asset', 'physical_asset'
    ).order_by('-date', '-uploaded_at')
    if q:
        docs_qs = docs_qs.filter(
            Q(title__icontains=q)
            | Q(notes__icontains=q)
            | Q(file__icontains=q)
            | Q(extracted_text__icontains=q)
            | Q(real_estate__name__icontains=q)
            | Q(loan__name__icontains=q)
            | Q(insurance_policy__name__icontains=q)
            | Q(pension__provider__icontains=q)
            | Q(asset__name__icontains=q)
            | Q(physical_asset__name__icontains=q)
        )
    doc_results = [serialize_document(d) for d in docs_qs[:100]]

    # 2. Real Estate & Loans
    re_results = []
    if matches_scope('real_estate_loans'):
        re_qs = RealEstate.objects.filter(user=user).order_by('name')
        loan_qs = Loan.objects.filter(user=user).select_related('real_estate').order_by('name')
        comp_qs = PropertyComponent.objects.filter(real_estate__user=user).select_related('real_estate').order_by('name')
        if q:
            re_qs = re_qs.filter(Q(name__icontains=q) | Q(location__icontains=q) | Q(current_tenant__icontains=q))
            loan_qs = loan_qs.filter(Q(name__icontains=q) | Q(provider__icontains=q) | Q(account_number__icontains=q) | Q(notes__icontains=q))
            comp_qs = comp_qs.filter(Q(name__icontains=q) | Q(notes__icontains=q) | Q(real_estate__name__icontains=q))
        else:
            re_qs = re_qs[:10]
            loan_qs = loan_qs[:10]
            comp_qs = comp_qs[:10]

        for r in re_qs[:50]:
            re_results.append({
                'kind': _('Real Estate'),
                'title': r.name,
                'subtitle': f"{r.get_property_type_display()} · {r.location}" if r.location else r.get_property_type_display(),
                'amount': float(r.property_value or 0),
                'url': reverse('finance:real_estate_loans'),
            })
        for l in loan_qs[:50]:
            re_results.append({
                'kind': _('Loan'),
                'title': l.name,
                'subtitle': f"{l.provider or ''}{' · ' + l.real_estate.name if l.real_estate else ''}".strip(' ·'),
                'amount': float(l.nominal_amount or 0),
                'url': f"{reverse('finance:real_estate_loans')}?tab=loans",
            })
        for c in comp_qs[:50]:
            re_results.append({
                'kind': _('Property Component'),
                'title': c.name,
                'subtitle': f"{c.real_estate.name} · {c.get_component_type_display()}",
                'amount': float(c.estimated_cost or 0),
                'url': f"{reverse('finance:real_estate_loans')}?tab=components",
            })

    # 3. Insurance & Pensions
    ins_pen_results = []
    if matches_scope('insurance_pensions'):
        ins_qs = InsurancePolicy.objects.filter(user=user).order_by('name')
        pen_qs = Pension.objects.filter(user=user).order_by('provider')
        if q:
            ins_qs = ins_qs.filter(Q(name__icontains=q) | Q(provider__icontains=q) | Q(policy_number__icontains=q) | Q(notes__icontains=q))
            pen_qs = pen_qs.filter(Q(provider__icontains=q) | Q(notes__icontains=q))
        else:
            ins_qs = ins_qs[:10]
            pen_qs = pen_qs[:10]

        for p in ins_qs[:50]:
            ins_pen_results.append({
                'kind': _('Insurance'),
                'title': p.name,
                'subtitle': f"{p.get_insurance_type_display()}{' · ' + p.provider if p.provider else ''}",
                'amount': float(p.premium_amount or 0),
                'url': f"{reverse('finance:pension_plan')}?tab=insurances",
            })
        for p in pen_qs[:50]:
            ins_pen_results.append({
                'kind': _('Pension'),
                'title': p.provider,
                'subtitle': p.get_pension_type_display(),
                'amount': float(p.expected_payout_at_retirement or p.current_value or 0),
                'url': f"{reverse('finance:pension_plan')}?tab=pensions",
            })

    # 4. Assets & Physical Assets
    asset_results = []
    if matches_scope('assets'):
        a_qs = Asset.objects.filter(user=user).order_by('name')
        pa_qs = PhysicalAsset.objects.filter(user=user).order_by('name')
        if q:
            a_qs = a_qs.filter(Q(name__icontains=q) | Q(institution__icontains=q) | Q(isin_ticker__icontains=q))
            pa_qs = pa_qs.filter(Q(name__icontains=q) | Q(location__icontains=q))
        else:
            a_qs = a_qs[:10]
            pa_qs = pa_qs[:10]

        for a in a_qs[:50]:
            asset_results.append({
                'kind': _('Account / Asset'),
                'title': a.name,
                'subtitle': f"{a.get_asset_type_display()}{' · ' + a.institution if a.institution else ''}",
                'amount': float(a.value or 0),
                'url': reverse('finance:assets_overview'),
            })
        for pa in pa_qs[:50]:
            asset_results.append({
                'kind': _('Physical Asset'),
                'title': pa.name,
                'subtitle': pa.location or _('Physical Asset'),
                'amount': float(pa.value or 0),
                'url': reverse('finance:assets_overview'),
            })

    # 5. Cashflows & One-Time Events
    cf_results = []
    if matches_scope('cashflows'):
        cf_qs = CashFlowSource.objects.filter(user=user).select_related('category').order_by('name')
        ev_qs = OneTimeEvent.objects.filter(user=user).order_by('-date')
        if q:
            cf_qs = cf_qs.filter(Q(name__icontains=q) | Q(category__name__icontains=q))
            ev_qs = ev_qs.filter(Q(name__icontains=q))
        else:
            cf_qs = cf_qs[:10]
            ev_qs = ev_qs[:10]

        for c in cf_qs[:50]:
            cf_results.append({
                'kind': _('Income') if c.is_income else _('Expense'),
                'title': c.name,
                'subtitle': f"{c.get_frequency_display()}{' · ' + c.category.name if c.category else ''}",
                'amount': float(c.value or 0),
                'url': reverse('finance:cash_flow_list'),
            })
        for ev in ev_qs[:50]:
            cf_results.append({
                'kind': _('One-Time Event'),
                'title': ev.name,
                'subtitle': ev.date.strftime('%d.%m.%Y') if ev.date else '',
                'amount': float(ev.amount or 0),
                'url': reverse('finance:cash_flow_list'),
            })

    counts = {
        'documents': len(doc_results),
        'real_estate_loans': len(re_results),
        'insurance_pensions': len(ins_pen_results),
        'assets': len(asset_results),
        'cashflows': len(cf_results),
    }
    counts['all'] = sum(counts.values())

    return {
        'query': q,
        'scope': scope,
        'counts': counts,
        'doc_results': doc_results if matches_scope('documents') else [],
        're_results': re_results,
        'ins_pen_results': ins_pen_results,
        'asset_results': asset_results,
        'cf_results': cf_results,
    }
