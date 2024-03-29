from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_bootstrap import Bootstrap5
from flask_session import Session
from flask_wtf import FlaskForm
from mysql.connector import IntegrityError, DataError
from wtforms import StringField, PasswordField, IntegerField, FloatField, SelectField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Optional, Length, Regexp, NumberRange, ValidationError
from datetime import date, datetime, timedelta

from . import tables, sanitize, reports, host_toolkit
from .consts import AMENITIES_CHOICES, TYPE_CHOICES

app = Flask(__name__)
app.secret_key = 'B5F61F92-EADD-4952-A165-A39568B83603'

app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

Bootstrap5(app)


def form_endpoint(form, template_path: str, on_submit: callable, next_location: str = None, template_args: dict = {}):
    if not isinstance(form, FlaskForm):
        # Instantiate form class
        form = form()

    if form.validate_on_submit():
        try:
            on_submit(form)
            if next_location:
                return redirect(next_location)

        except ValidationError as e:
            flash(str(e), 'danger')
        except (IntegrityError, DataError) as e:
            flash(e.msg, 'danger')

    return render_template(template_path, form=form, **template_args)

def validate_dob(field):
    if not field.data:
        return
    try:
        dob_date = datetime.strptime(field.data, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError("Invalid date format. Please use YYYY-MM-DD.")

    current_date = datetime.now().date()
    max_dob_date = current_date - timedelta(days=365 * 18)
    min_dob_date = current_date - timedelta(days=365 * 100)

    if dob_date >= current_date:
        raise ValidationError("Date of Birth cannot be in the future.")

    if dob_date >= max_dob_date:
        raise ValidationError("Date of Birth should be at least 18 years ago.")

    if dob_date <= min_dob_date:
        raise ValidationError("Date of Birth should be less than 100 years ago.")
        
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    class Form(FlaskForm):
        sin = StringField('SIN', validators=[DataRequired(), Regexp(sanitize.sin_pattern, 0, 'Must have the form xxx-xxx-xxx.')], render_kw={"placeholder": "xxx-xxx-xxx"})

        name = StringField('Name', validators=[DataRequired(), Length(1, 63)])
        dob = StringField('Date of Birth', validators=[DataRequired(), Length(1, 15)], render_kw={"placeholder": "YYYY-MM-DD"})
        address = StringField('Address', validators=[Length(0, 127)])
        occupation = StringField('Occupation', validators=[Length(0, 31)])

        username = StringField('Choose a Username', validators=[DataRequired(), Length(1, 63)])
        password = PasswordField('Choose a Password', validators=[Length(0, 63)])

        submit = SubmitField('Sign Up')
    
    def on_submit(form):
        validate_dob(form.dob)
        tables.users.sign_up(
            sin=sanitize.sin(form.sin.data),

            name=form.name.data,
            dob=form.dob.data,
            address=form.address.data,
            occupation=form.occupation.data,

            username=form.username.data
        )

    return form_endpoint(Form, 'sign-up.html',
                         next_location='/dashboard',
                         on_submit=on_submit)

@app.route('/log-in', methods=['GET', 'POST'])
def log_in():
    class Form(FlaskForm):
        username = StringField('Username', validators=[DataRequired(), Length(1, 63)])
        password = PasswordField('Password', validators=[Length(0, 63)])
        submit = SubmitField('Log In')

    def on_submit(form):
        tables.users.log_in(username=form.username.data)

    return form_endpoint(Form, 'log-in.html',
                         next_location='/dashboard',
                         on_submit=on_submit)

@app.route('/dashboard')
def dashboard():
    return render_template(
        'dashboard.html',
        user=tables.users.current(),
    )

@app.route('/become-a-renter', methods=['GET', 'POST'])
def become_a_renter():
    class Form(FlaskForm):
        card_num = StringField('Credit Card Number', validators=[Regexp(sanitize.card_num_pattern, 0, 'Must have the form xxxx-xxxx-xxxx-xxxx.')])

        submit = SubmitField('Submit')

    def on_submit(form):
        tables.users.become_renter(sanitize.card_num(form.card_num.data))
        flash('You are now a renter!', 'success')

    return form_endpoint(
        Form, 'become-a-renter.html',
        on_submit=on_submit,
        next_location='/dashboard',
        template_args={
            'user': tables.users.current()
        }
    )

@app.route('/become-a-host', methods=['GET', 'POST'])
def become_a_host():
    class Form(FlaskForm):
        submit = SubmitField('I Agree')

    def on_submit(form):
        tables.users.become_host()
        flash('You are now a host!', 'success')

    return form_endpoint(
        Form, 'become-a-host.html',
        on_submit=on_submit,
        next_location='/dashboard',
        template_args={
            'user': tables.users.current()
        }
    )

@app.route('/my-profile', methods=['GET', 'POST'])
@app.route('/my-profile/delete', methods=['POST'])
def my_profile():
    class Form(FlaskForm):
        id = StringField('User ID', render_kw={'readonly': True})

        sin = StringField('SIN', validators=[DataRequired(), Regexp(sanitize.sin_pattern, 0, 'Must have the form xxx-xxx-xxx.')])

        name = StringField('Name', validators=[DataRequired(), Length(1, 63)])
        dob = StringField('Date of Birth', validators=[DataRequired(), Length(1, 15)])
        address = StringField('Address', validators=[Length(0, 127)])
        occupation = StringField('Occupation', validators=[Length(0, 31)])

        username = StringField('Username', validators=[DataRequired(), Length(1, 63)])
        password = PasswordField('Password', validators=[Length(0, 63)])

        submit = SubmitField('Save Changes')
        delete = SubmitField('Delete Account', render_kw={'class': 'btn-light btn-outline-danger', 'formaction': '/my-profile/delete'})

    is_delete_request = (request.path.lower() == '/my-profile/delete')

    def on_submit(form):
        if is_delete_request:
            tables.users.delete_current()
            flash('Your account was deleted.', 'success')
        else:
            validate_dob(form.dob)
            tables.users.update_profile(
                sin=sanitize.sin(form.sin.data),

                name=form.name.data,
                dob=form.dob.data,
                address=form.address.data,
                occupation=form.occupation.data,

                username=form.username.data
            )
            flash('Your changes have been saved.', 'success')

    user = tables.users.current()

    form = Form()
    if not form.is_submitted():
        form.id.data = user.id

        form.sin.data = str(user.sin)

        form.name.data = user.name
        form.dob.data = str(user.dob)
        form.address.data = user.address
        form.occupation.data = user.occupation

        form.username.data = user.username

    return form_endpoint(
        form, 'my-profile.html',
        on_submit=on_submit,
        next_location=('/' if is_delete_request else None),
        template_args={
            'user': user
        }
    )

@app.route('/my-listings')
def my_listings():
    return render_template(
        'my-listings.html',
        user=tables.users.current(),
        listings=tables.listings.owned_by_current_user()
    )

@app.route('/my-listings/<id>/delete', methods=['POST'])
def listing_delete(id):
    tables.listings.delete(id)
    flash('Listing was deleted.', 'success')
    return redirect('/my-listings')

class ListingEditForm(FlaskForm):
    id = StringField('Listing ID', render_kw={'readonly': True})

    country = StringField('Country', validators=[Length(1, 31)])
    city = StringField('City', validators=[Length(1, 31)])
    postal = StringField('Postal', validators=[Length(6, 6)])
    address = StringField('Address', validators=[Length(0, 127)])

    lat = FloatField('Latitude', validators=[DataRequired()])
    lon = FloatField('Longitude', validators=[DataRequired()])

    type = SelectField(
        'Type',
        choices=TYPE_CHOICES
    )
    amenities = SelectMultipleField(
        'Amenities (select multiple)',
        choices=AMENITIES_CHOICES,
        render_kw={
            'size': '10'
        }
    )

    submit = SubmitField('Save Changes')

@app.route('/my-listings/create', methods=['GET', 'POST'])
def listing_create():
    current_user = tables.users.current()

    def on_submit(form):
        tables.listings.create(
            owner_id=current_user.id,

            country=form.country.data,
            city=form.city.data,
            postal=form.postal.data,
            address=form.address.data,

            lat=form.lat.data,
            lon=form.lon.data,

            type=form.type.data,
            amenities=', '.join(form.amenities.data),
        )
        flash('Listing created.', 'success')

    form = ListingEditForm()
    if not form.is_submitted():
        del form.id

    return form_endpoint(
        form, 'listing-create.html',
        on_submit=on_submit,
        next_location='/my-listings',
        template_args={
            'user': current_user
        }
    )

@app.route('/my-listings/<id>/edit', methods=['GET', 'POST'])
def listing_edit(id):
    def on_submit(form):
        tables.listings.update(
            id=id,

            country=form.country.data,
            city=form.city.data,
            postal=form.postal.data,
            address=form.address.data,

            lat=form.lat.data,
            lon=form.lon.data,

            type=form.type.data,
            amenities=', '.join(form.amenities.data),
        )
        flash('Your changes have been saved.', 'success')

    listing = tables.listings.for_id(id)

    form = ListingEditForm()
    if not form.is_submitted():
        form.id.data = listing.id

        form.country.data = listing.country
        form.city.data = listing.city
        form.postal.data = listing.postal
        form.address.data = listing.address

        form.lat.data = listing.lat
        form.lon.data = listing.lon

        form.type.data = listing.type
        form.amenities.data = listing.amenities.split(', ')

    return form_endpoint(
        form, 'listing-edit.html',
        on_submit=on_submit,
        next_location='/my-listings',
        template_args={
            'user': tables.users.current(),
            'listing': listing
        }
    )

@app.route('/my-listings/<id>/schedule')
def listing_schedule(id):
    listing = tables.listings.for_id(id)
    today = datetime.now().date()
    two_weeks_ago = today - timedelta(days=15)

    return render_template(
        'listing-schedule.html',
        user=tables.users.current(),
        listing=listing,
        slots=tables.booking_slots.all_for_listing(listing),
        pastslots=tables.booking_slots.past_slots_for_listing(listing),
        two_weeks_ago=two_weeks_ago
    )

@app.route('/my-listings/<listing_id>/schedule/<renter_id>/rate-renter', methods=['GET', 'POST'])
def rate_renter(listing_id, renter_id):
    class Form(FlaskForm):
        rating = FloatField('Rating', validators=[NumberRange(0, 5)], render_kw={"placeholder": "ratings are between 0 and 5"})
        comment = StringField('Comment', render_kw={"placeholder": "Amazing!"})

        submit = SubmitField('Submit Comments and Rating', render_kw={'class': 'btn-primary'})

    current_user = tables.users.current()

    def on_submit(form):
        tables.user_comments.renter_comments(
            current_user.id,
            renter_id,
            form.comment.data,
            form.rating.data
        )
        flash('Rating submitted.', 'success')

    return form_endpoint(
        Form, 'renter-rate.html',
        on_submit=on_submit,
        next_location=f'/my-listings/{listing_id}/schedule',
        template_args={
            'user': current_user,
            'renter': tables.users.for_id(renter_id),
            'listing_id': listing_id
        }
    )

@app.route('/my-listings/<listing_id>/schedule/<slot_id>/delete', methods=['POST'])
def listing_schedule_delete(listing_id, slot_id):
    tables.booking_slots.delete(slot_id)
    flash('Booking slot was deleted.', 'success')
    return redirect(f'/my-listings/{listing_id}/schedule')

@app.route('/my-listings/<listing_id>/schedule/<slot_id>/retract', methods=['POST'])
def listing_schedule_retract(listing_id, slot_id):
    tables.booking_slots.mark_unavailable(slot_id)
    flash(f'Availability retracted for {tables.booking_slots.for_id(slot_id).date}.', 'success')
    return redirect(f'/my-listings/{listing_id}/schedule')

@app.route('/my-listings/<listing_id>/schedule/<slot_id>/cancel', methods=['POST'])
def listing_schedule_cancel(listing_id, slot_id):
    tables.bookings.delete(slot_id)
    flash(f'Booking on {tables.booking_slots.for_id(slot_id).date} cancelled.', 'success')
    return redirect(f'/my-listings/{listing_id}/schedule')

@app.route('/my-listings/<listing_id>/schedule/<slot_id>/set-price', methods=['GET', 'POST'])
def listing_schedule_slot_set_price(listing_id, slot_id):
    class Form(FlaskForm):
        listing_id = StringField('Listing ID', render_kw={'readonly': True})
        slot_id = StringField('Slot ID', render_kw={'readonly': True})

        rental_price = FloatField('Rental Price', validators=[NumberRange(min=0)])

        submit = SubmitField('Post Offer', render_kw={'class': 'btn-success'})

    slot = tables.booking_slots.for_id(slot_id)
    listing = slot.listing

    def on_submit(form):
        if slot.date < date.today():
            flash('Cannot change price for a day in the past.', 'danger')
            return
    
        tables.booking_slots.update(
            id=slot.id,

            rental_price=form.rental_price.data
        )
        flash(f'Made available on {slot.date}.', 'success')

    form = Form()
    if not form.is_submitted():
        form.listing_id.data = listing.id
        form.slot_id.data = slot.id

        form.rental_price.data = slot.rental_price

    return form_endpoint(
        form, 'listing-schedule-slot-set-price.html',
        on_submit=on_submit,
        next_location=f'/my-listings/{listing_id}/schedule',
        template_args={
            'user': tables.users.current(),
            'listing': listing,
            'slot': slot,
            'price_suggestion': host_toolkit.suggest_price(listing),
            'amenity_suggestions': host_toolkit.suggest_amenities(listing)
        }
    )

@app.route('/my-listings/<listing_id>/schedule/<slot_id>/info')
def listing_schedule_slot_info(listing_id, slot_id):
    slot = tables.booking_slots.for_id(slot_id)
    cancellations = tables.bookings.cancellations(slot_id)

    return render_template(
        'listing-schedule-slot-info.html',
        user=tables.users.current(),
        listing=slot.listing,
        slot=slot,
        renter=(slot.renter_id and tables.users.for_id(slot.renter_id)),
        cancellations=cancellations
    )

def add_booking_slots(listing_id, start_date: date, end_date: date):
    for day_offset in range(0, (end_date - start_date).days + 1):
        tables.booking_slots.add(
            listing_id=listing_id,
            date=start_date + timedelta(days=day_offset)
        )

    flash(f'{start_date} thru {end_date} added to schedule.', 'success')

@app.route('/my-listings/<listing_id>/schedule/add-week-of-slots', methods=['POST'])
def listing_schedule_add_week_of_slots(listing_id):
    listing = tables.listings.for_id(listing_id)
    latest_slot = tables.booking_slots.latest_for_listing(listing)

    start_date = (latest_slot.date if latest_slot else date.today()) + timedelta(days=1)
    end_date = start_date + timedelta(days=6)

    add_booking_slots(listing_id, start_date, end_date)

    return redirect(f'/my-listings/{listing_id}/schedule')

@app.route('/my-listings/<listing_id>/schedule/add-slots', methods=['GET', 'POST'])
def listing_schedule_add_slots(listing_id):
    class Form(FlaskForm):
        start_date = StringField('Start Date', validators=[Length(1, 15)], render_kw={"placeholder": "YYYY-MM-DD"})
        end_date = StringField('End Date', validators=[Length(1, 15)], render_kw={"placeholder": "YYYY-MM-DD"})

        submit = SubmitField('Add Days to Schedule', render_kw={'class': 'btn-primary'})

    def on_submit(form):
        add_booking_slots(listing_id, sanitize.date(form.start_date.data), sanitize.date(form.end_date.data))
    
    return form_endpoint(
        Form, 'listing-schedule-add-slots.html',
        on_submit=on_submit,
        next_location=f'/my-listings/{listing_id}/schedule',
        template_args={
            'user': tables.users.current(),
            'listing': tables.listings.for_id(listing_id)
        }
    )

@app.route('/my-rentals')
def my_rentals():
    id=tables.users.current().id
    today = datetime.now().date()
    two_weeks_ago = today - timedelta(days=15)
    return render_template(
        'my-rentals.html',
        user=tables.users.current(),
        rentals=tables.bookings.rentals_for_id(id),
        pastrentals=tables.bookings.past_rentals_for_id(id),
        two_weeks_ago=two_weeks_ago
    )

@app.route('/my-rentals/<id>/delete', methods=['POST'])
def rental_delete(id):
    tables.bookings.delete(id)
    flash('Rental was deleted.', 'success')
    return redirect('/my-rentals')

@app.route('/my-rentals/<listing_id>/rate', methods=['GET', 'POST'])
def rental_rate(listing_id):
    class Form(FlaskForm):
        rating = FloatField('Rating', validators=[NumberRange(0, 5)], render_kw={"placeholder": "ratings are between 0 and 5"})
        comment = StringField('Comment', render_kw={"placeholder": "Amazing!"})

        submit = SubmitField('Submit Comments and Rating', render_kw={'class': 'btn-primary'})

    current_user = tables.users.current()

    def on_submit(form):
        tables.listing_comments.create(
            current_user.id,
            listing_id,
            form.comment.data,
            form.rating.data
        )
        flash('Rating submitted.', 'success')

    return form_endpoint(
        Form, 'rental-rate.html',
        on_submit=on_submit,
        next_location='/my-rentals',
        template_args={
            'user': current_user
        }
    )


@app.route('/my-rentals/<host_id>/rate-host', methods=['GET', 'POST'])
def rate_host(host_id):
    class Form(FlaskForm):
        rating = FloatField('Rating', validators=[NumberRange(0, 5)], render_kw={"placeholder": "ratings are between 0 and 5"})
        comment = StringField('Comment', render_kw={"placeholder": "Amazing!"})

        submit = SubmitField('Submit Comments and Rating', render_kw={'class': 'btn-primary'})

    current_user = tables.users.current()

    def on_submit(form):
        tables.user_comments.host_comment(
            current_user.id,
            host_id,
            form.comment.data,
            form.rating.data
        )
        flash('Rating submitted.', 'success')

    return form_endpoint(
        Form, 'host-rate.html',
        on_submit=on_submit,
        next_location='/my-rentals',
        template_args={
            'user': current_user,
            'host': tables.users.for_id(host_id)
        }
    )

@app.route('/listings', methods=['GET', 'POST'])
def listings():
    class Form(FlaskForm):
        latitude = FloatField('Latitude', validators=[Optional()], render_kw={"placeholder": "43.784093"})
        longitude = FloatField('Longitude', validators=[Optional()], render_kw={"placeholder": "-79.186527"})
        max_distance = FloatField('Max Distance (km; default: 5km)', validators=[Optional()], render_kw={"placeholder": "5"})

        max_price = FloatField('Max Price', validators=[Optional()], render_kw={"placeholder": "1000"})
        min_price = FloatField('Min Price', validators=[Optional()], render_kw={"placeholder": "100"})
        sort_by_price = SelectField('Sort By Price', validators=[Optional()], choices=['None', 'High To Low', 'Low To High'])

        postal_code = StringField('Postal Code (Same and Adjacent)', validators=[Optional(), Length(6, 6)], render_kw={"placeholder": "A1B2C3"})
        address = StringField('Address (Exact Match)', validators=[Optional()], render_kw={"placeholder": "66 Gerrard St E"})

        start_date = StringField('Booking Period Start', validators=[Optional()], render_kw={"placeholder": "YYYY-MM-DD"})
        end_date = StringField('Booking Period End', validators=[Optional()], render_kw={"placeholder": "YYYY-MM-DD"})

        type = SelectField('Type', choices=[None, *TYPE_CHOICES])
        amenities = SelectMultipleField(
            'Amenities (Select Multiple)',
            choices=AMENITIES_CHOICES,
            render_kw={
                'size': '10'
            }
        )

        submit = SubmitField('Apply Filters')


    def on_submit(form):
        pass
    listings = []

    form = Form()
    if form.is_submitted():
        filters = []

        if form.max_price.data:
            filters.append(('rental_price',form.max_price.data, '<='))
        if form.min_price.data:
            filters.append(('rental_price',form.min_price.data, '>='))
        if form.sort_by_price.data:
            filters.append(('sort',form.sort_by_price.data, 'sort'))
        if form.postal_code.data:
            filters.append(('postal',form.postal_code.data[:3],'='))
        if form.address.data:
            filters.append(('address',form.address.data,'='))
        if form.type.data:
            filters.append(('type',form.type.data,'='))
        if form.amenities.data:
            filters.append(('amenities',form.amenities.data,'LIKE'))
        if form.start_date.data:
            filters.append(('date',form.start_date.data,'>='))   
        if form.end_date.data:
            filters.append(('date',form.end_date.data,'<='))
        
        if form.latitude.data and form.longitude.data:
            if not form.max_distance.data:
                form.max_distance.data = 5
            filters.append(('distance',(form.latitude.data,form.longitude.data,form.max_distance.data),'<='))

        id = tables.users.current().id
        listings = tables.listings.search(id,filters)
        

    return form_endpoint(
        form, 'listings.html',
        on_submit=on_submit,
        template_args={
            'user': tables.users.current(),
            'listings': listings
        }
    )

@app.route('/listings/<id>/book', methods=['GET','POST'])
def book_listing(id):
    tables.bookings.book(id)
    flash('Rental was booked.', 'success')
    return redirect('/listings')

@app.route('/reports', methods=['GET', 'POST'])
def reports_():
    class Form(FlaskForm):
        start_date = StringField('Start Date', validators=[Length(1, 15)], render_kw={"placeholder": "YYYY-MM-DD"})
        end_date = StringField('End Date', validators=[Length(1, 15)], render_kw={"placeholder": "YYYY-MM-DD"})

        submit = SubmitField('Generate Report')

    def on_submit(form):
        pass

    report = []

    form = Form()
    if form.is_submitted():
        start_date = form.start_date.data
        end_date = form.end_date.data

        report.append({
            'title': 'Bookings by City',
            'records': reports.count_bookings_by_city(start_date, end_date)
        })
        report.append({
            'title': 'Bookings by City and Postal Code',
            'records': reports.count_bookings_by_city_postal(start_date, end_date)
        })

        report.append({
            'title': 'Listings by Country',
            'records': reports.count_listings_by_country()
        })
        report.append({
            'title': 'Listings by Country and City',
            'records': reports.count_listings_by_country_city()
        })
        report.append({
            'title': 'Listings by Country, City, and Postal Code',
            'records': reports.count_listings_by_country_city_postal()
        })

        for country, in reports.all_countries():
            report.append({
                'title': f'Top Hosts in {country}',
                'records': reports.top_hosts_in_country(country)
            })
        for country, city in reports.all_country_cities():
            report.append({
                'title': f'Top Hosts in {city}, {country}',
                'records': reports.top_hosts_in_country_city(country, city)
            })

        for country, city in reports.all_country_cities():
            report.append({
                'title': f'Potential Commercial Hosts in {city}, {country}',
                'records': reports.potential_commercial_hosts(country, city)
            })

        report.append({
            'title': 'Top Renters by Bookings',
            'records': reports.top_renters(start_date, end_date)
        })
        for country, city in reports.all_country_cities():
            report.append({
                'title': f'Top Renters in {city}, {country} by Bookings (≥2)',
                'records': reports.top_renters_by_country_city(start_date, end_date, country, city)
            })

        report.append({
            'title': 'Top Hosts by Cancellations',
            'records': reports.top_cancelling_hosts(start_date, end_date)
        })
        report.append({
            'title': 'Top Renters by Cancellations',
            'records': reports.top_cancelling_renters(start_date, end_date)
        })

        report.append({
            'title': 'Top Noun Phrases by Listing Comment',
            'records': reports.top_noun_phrases_by_listing_comment()
        })
        report.append({
            'title': 'Top Noun Phrases in All Listing Comments',
            'records': reports.top_noun_phrases_in_listing_comments()
        })

    return form_endpoint(
        Form, 'reports.html',
        on_submit=on_submit,
        template_args={
            'user': tables.users.current(),
            'report': report
        }
    )

if __name__ == '__main__':
    app.run()
