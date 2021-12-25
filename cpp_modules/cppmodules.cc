#include <Python.h>

#include <set>
#include <vector>
#include <algorithm>
#include <unordered_set>

static PyObject* cpp_crossing_flows(PyObject*, PyObject* args) {
    PyObject* flow_tuples = NULL;
    if (!PyArg_ParseTuple(args, "O", &flow_tuples)) {
        return NULL;
    }

    std::vector<std::pair<int, std::set<std::pair<int, int>>>> flows;
    if (flow_tuples == NULL) {
        PyErr_SetString(PyExc_TypeError, "no flows");
        return NULL;
    }
    PyObject* i = PyObject_GetIter(flow_tuples);
    if (i == NULL) {
        return NULL;
    }
    PyObject* ftuple;
    while ((ftuple = PyIter_Next(i))) {
        PyObject* j = PyObject_GetIter(ftuple);
        if (j == NULL) {
            return NULL;
        }

        int flow_id;
        PyObject* fid = PyIter_Next(j);
        if (!PyLong_Check(fid)) {
            PyErr_SetString(PyExc_TypeError, "invalid flow_id");
            return NULL;
        }
        flow_id = PyLong_AsLong(fid);

        std::set<std::pair<int, int>> edges;
        PyObject* pyedges = PyIter_Next(j);
        PyObject* k = PyObject_GetIter(pyedges);
        if (k == NULL) {
            return NULL;
        }
        PyObject* eo;
        while ((eo = PyIter_Next(k))) {
            PyObject* l = PyObject_GetIter(eo);
            if (l == NULL) {
                return NULL;
            }
            std::vector<int> e;
            PyObject* vo;
            while ((vo = PyIter_Next(l))) {
                if (!PyLong_Check(vo)) {
                    PyErr_SetString(PyExc_TypeError, "invalid graph");
                    return NULL;
                }
                e.push_back(PyLong_AsLong(vo));
            }
            assert(e.size() == 2);
            edges.insert(std::make_pair(e[0], e[1]));
        }
        
        flows.push_back(std::make_pair(flow_id, edges));
    }

    PyObject* crossings = PySet_New(NULL);
    std::vector<std::pair<int, std::set<std::pair<int, int>>>>::iterator i_iter, j_iter;
    for (i_iter = flows.begin(); i_iter != flows.end(); i_iter++) {
        for (j_iter = std::next(i_iter); j_iter != flows.end(); j_iter++) {
            std::set<std::pair<int, int>> intersection_set, i_set, j_set;
            i_set = (*i_iter).second;
            j_set = (*j_iter).second;
            std::set_intersection(i_set.begin(), i_set.end(), 
                                  j_set.begin(), j_set.end(), 
                                  std::inserter(intersection_set, intersection_set.end()));
            if (intersection_set.size()) {
                PySet_Add(crossings, Py_BuildValue("(ii)", (*i_iter).first, (*j_iter).first));
            }
        }
    }

    return crossings;
}

static PyObject* cpp_crossings_for_a_flow(PyObject*, PyObject* args) {
    PyObject* target_flow_tuple = NULL;
    PyObject* flow_tuples = NULL;
    if (!PyArg_ParseTuple(args, "OO", &target_flow_tuple, &flow_tuples)) {
        return NULL;
    }

    // make target_flow
    std::pair<int, std::set<std::pair<int, int>>> target_flow;
    if (target_flow_tuple == NULL) {
        PyErr_SetString(PyExc_TypeError, "no flows");
        return NULL;
    }
    PyObject* i = PyObject_GetIter(target_flow_tuple);
    if (i == NULL) {
        return NULL;
    }

    int flow_id;
    PyObject* fid = PyIter_Next(i);
    if (!PyLong_Check(fid)) {
        PyErr_SetString(PyExc_TypeError, "invalid flow_id");
        return NULL;
    }
    flow_id = PyLong_AsLong(fid);

    std::set<std::pair<int, int>> edges;
    PyObject* pyedges = PyIter_Next(i);
    PyObject* j = PyObject_GetIter(pyedges);
    if (j == NULL) {
        return NULL;
    }
    PyObject* eo;
    while ((eo = PyIter_Next(j))) {
        PyObject* k = PyObject_GetIter(eo);
        if (k == NULL) {
            return NULL;
        }
        std::vector<int> e;
        PyObject* vo;
        while ((vo = PyIter_Next(k))) {
            if (!PyLong_Check(vo)) {
                PyErr_SetString(PyExc_TypeError, "invalid graph");
                return NULL;
            }
            e.push_back(PyLong_AsLong(vo));
        }
        assert(e.size() == 2);
        edges.insert(std::make_pair(e[0], e[1]));
    }
    target_flow = std::make_pair(flow_id, edges);

    // make flows
    std::vector<std::pair<int, std::set<std::pair<int, int>>>> flows;
    if (flow_tuples == NULL) {
        PyErr_SetString(PyExc_TypeError, "no flows");
        return NULL;
    }
    i = PyObject_GetIter(flow_tuples);
    if (i == NULL) {
        return NULL;
    }
    PyObject* ftuple;
    while ((ftuple = PyIter_Next(i))) {
        PyObject* j = PyObject_GetIter(ftuple);
        if (j == NULL) {
            return NULL;
        }

        int flow_id;
        PyObject* fid = PyIter_Next(j);
        if (!PyLong_Check(fid)) {
            PyErr_SetString(PyExc_TypeError, "invalid flow_id");
            return NULL;
        }
        flow_id = PyLong_AsLong(fid);

        std::set<std::pair<int, int>> edges;
        PyObject* pyedges = PyIter_Next(j);
        PyObject* k = PyObject_GetIter(pyedges);
        if (k == NULL) {
            return NULL;
        }
        PyObject* eo;
        while ((eo = PyIter_Next(k))) {
            PyObject* l = PyObject_GetIter(eo);
            if (l == NULL) {
                return NULL;
            }
            std::vector<int> e;
            PyObject* vo;
            while ((vo = PyIter_Next(l))) {
                if (!PyLong_Check(vo)) {
                    PyErr_SetString(PyExc_TypeError, "invalid graph");
                    return NULL;
                }
                e.push_back(PyLong_AsLong(vo));
            }
            assert(e.size() == 2);
            edges.insert(std::make_pair(e[0], e[1]));
        }
        
        flows.push_back(std::make_pair(flow_id, edges));
    }

    std::unordered_set<int> crossings;
    std::vector<std::pair<int, std::set<std::pair<int, int>>>>::iterator iter;
    for (iter = flows.begin(); iter != flows.end(); iter++) {
        if (target_flow.first != (*iter).first) {
            std::set<std::pair<int, int>> intersection_set;
            std::set_intersection(target_flow.second.begin(), target_flow.second.end(), 
                                  (*iter).second.begin(), (*iter).second.end(), 
                                  std::inserter(intersection_set, intersection_set.end()));
            if (intersection_set.size()) {
                crossings.insert((*iter).first);
            }
        }
    }

    return Py_BuildValue("i", crossings.size());
}

static PyMethodDef mod_methods[] = {
    {"crossing_flows", cpp_crossing_flows, METH_VARARGS},
    {"crossings_for_a_flow", cpp_crossings_for_a_flow, METH_VARARGS},
    {NULL},
};

static struct PyModuleDef mod_def = {
    PyModuleDef_HEAD_INIT,
    "cpp_modules",
    "crossing_flows written in C",
    -1,
    mod_methods
};

//module creator
PyMODINIT_FUNC PyInit_cpp_modules(void)
{
    return PyModule_Create(&mod_def);
}