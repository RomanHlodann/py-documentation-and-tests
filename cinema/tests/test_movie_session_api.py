from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from cinema.tests.test_movie_api import (
    sample_movie,
    sample_movie_session
)
from cinema.serializers import MovieSessionListSerializer, MovieSessionSerializer
from cinema.models import Order, Ticket, MovieSession

MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def detail_movie_session_url(movie_session_id: int):
    return reverse("cinema:moviesession-detail", args=[movie_session_id])


def remove_key_from_dict(dict_: dict, key_to_delete):
    return {
        key: value
        for key, value in dict_.items()
        if key != key_to_delete
    }


def sample_ticket(user_id: int, movie_session: MovieSession, **params):
    order = Order.objects.create(user_id=user_id)
    defaults = {
        "movie_session": movie_session,
        "order": order,
        "row": 1,
        "seat": 1
    }
    defaults.update(params)

    return Ticket.objects.create(**defaults)


class TestUnauthorizedMovieSessionView(TestCase):
    def test_auth_required(self):
        client = APIClient()
        res = client.get(MOVIE_SESSION_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class TestAuthorizedMovieSessionView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.movie_session = sample_movie_session(movie=self.movie)

    def test_movie_session_list_filter_by_date(self):
        movie_session = sample_movie_session(show_time="2022-06-03T00:00:00Z", movie=self.movie)

        serializer = MovieSessionListSerializer(movie_session)

        res = self.client.get(
            MOVIE_SESSION_URL,
            {"date": "2022-06-03"}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        filtered_data = remove_key_from_dict(
            dict(res.data[0]),
            "tickets_available"
        )
        self.assertEqual(filtered_data, serializer.data)

    def test_movie_session_list_filter_by_movie(self):
        movie = sample_movie(title="Oppenheimer")
        movie_session = sample_movie_session(
            movie=movie,
            show_time="2022-06-03T00:00:00Z"
        )

        serializer = MovieSessionListSerializer(movie_session)

        res = self.client.get(
            MOVIE_SESSION_URL,
            {"movie": movie.id}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        filtered_data = remove_key_from_dict(
            dict(res.data[0]),
            "tickets_available"
        )
        self.assertEqual(filtered_data, serializer.data)

    def test_create_movie_session_forbidden(self):
        data = {
            "show_time": "2022-06-02 14:00:00",
            "movie": 1,
            "cinema_hall": 1
        }
        res = self.client.post(MOVIE_SESSION_URL, data=data)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_tickets_available(self):
        sample_ticket(self.user.id, self.movie_session)
        sample_ticket(self.user.id, self.movie_session, seat=2)

        res = self.client.get(MOVIE_SESSION_URL)
        tickets_available = res.data[0]["tickets_available"]

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(tickets_available, 398)


class TestAdminMovieSessionView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.movie_session = sample_movie_session(movie=self.movie)

    def test_create_movie_session(self):
        data = {
            "show_time": "2022-06-02 14:00:00",
            "movie": 1,
            "cinema_hall": 1
        }
        res = self.client.post(MOVIE_SESSION_URL, data=data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie_session = MovieSession.objects.get(id=res.data["id"])
        serializer = MovieSessionSerializer(movie_session)

        self.assertEqual(res.data, serializer.data)
